import torch
import torch.nn as nn
import torch.nn.functional as F

class BasicConv(nn.Module):
    def __init__(self, in_channel, out_channel, kernel_size, stride, bias=True, norm=False, relu=True, transpose=False):
        super(BasicConv, self).__init__()
        if bias and norm:
            bias = False

        padding = kernel_size // 2
        layers = list()
        if transpose:
            padding = kernel_size // 2 -1
            layers.append(nn.ConvTranspose2d(in_channel, out_channel, kernel_size, padding=padding, stride=stride, bias=bias))
        else:
            layers.append(
                nn.Conv2d(in_channel, out_channel, kernel_size, padding=padding, stride=stride, bias=bias))
        if norm:
            layers.append(nn.BatchNorm2d(out_channel))
        if relu:
            layers.append(nn.GELU())
        self.main = nn.Sequential(*layers)

    def forward(self, x):
        return self.main(x)

class ResBlock(nn.Module):
    def __init__(self, in_channel, out_channel, filter=False):
        super(ResBlock, self).__init__()
        self.conv1 = BasicConv(in_channel, out_channel, kernel_size=3, stride=1, relu=True)
        self.conv2 = BasicConv(out_channel, out_channel, kernel_size=3, stride=1, relu=False)
        if filter:
            self.cubic_11 = cubic_attention(in_channel//2, group=1, kernel=11)
            self.cubic_7 = cubic_attention(in_channel//2, group=1, kernel=7)
            self.pool_att = SpecAtte(in_channel)

        self.filter = filter
    def forward(self, x):
        out = self.conv1(x)
        if self.filter:

            out = self.pool_att(out)
            out = torch.chunk(out, 2, dim=1)
            out_11 = self.cubic_11(out[0])
            out_7 = self.cubic_7(out[1])
            out = torch.cat((out_11, out_7), dim=1)

        out = self.conv2(out)
        return out + x

class cubic_attention(nn.Module):
    def __init__(self, dim, group, kernel) -> None:
        super().__init__()

        self.H_spatial_att = spatial_strip_att(dim, group=group, kernel=kernel)
        self.W_spatial_att = spatial_strip_att(dim, group=group, kernel=kernel, H=False)
        self.gamma = nn.Parameter(torch.zeros(dim,1,1))
        self.beta = nn.Parameter(torch.ones(dim,1,1))
    def forward(self, x):
        out = self.H_spatial_att(x)
        out = self.W_spatial_att(out)
        return self.gamma * out + x * self.beta

class spatial_strip_att(nn.Module):
    def __init__(self, dim, kernel=5, group=2, H=True) -> None:
        super().__init__()
        self.k = kernel
        pad = kernel // 2
        self.kernel = (1, kernel) if H else (kernel, 1)
        self.padding = (kernel//2, 1) if H else (1, kernel//2)

        self.group = group
        self.pad = nn.ReflectionPad2d((pad, pad, 0, 0)) if H else nn.ReflectionPad2d((0, 0, pad, pad))
        self.conv = nn.Conv2d(dim, group*kernel, kernel_size=1, stride=1, bias=False)
        self.ap = nn.AdaptiveAvgPool2d((1, 1))
        self.filter_act = nn.Sigmoid()

    def forward(self, x):
        filter = self.ap(x)
        filter = self.conv(filter)
        n, c, h, w = x.shape
        x = F.unfold(self.pad(x), kernel_size=self.kernel).reshape(n, self.group, c//self.group, self.k, h*w)
        
        n, c1, p, q = filter.shape
        filter = filter.reshape(n, c1//self.k, self.k, p*q).unsqueeze(2)
        filter = self.filter_act(filter)

        out = torch.sum(x * filter, dim=3).reshape(n, c, h, w)
        return out

class GlobalPoolStripAttention(nn.Module):
    def __init__(self, k) -> None:
        super().__init__()

        self.channel = k

        self.vert_low = nn.Parameter(torch.zeros(k, 1, 1))
        self.vert_high = nn.Parameter(torch.zeros(k, 1, 1))

        self.hori_low = nn.Parameter(torch.zeros(k, 1, 1))
        self.hori_high = nn.Parameter(torch.zeros(k, 1, 1))

        self.vert_pool = nn.AdaptiveAvgPool2d((1, None))
        self.hori_pool = nn.AdaptiveAvgPool2d((None, 1))


        self.gamma = nn.Parameter(torch.zeros(k,1,1))
        self.beta = nn.Parameter(torch.ones(k,1,1))

    def forward(self, x):

        hori_l = self.hori_pool(x) # 1,3,10,1
        hori_h = x - hori_l

        hori_out = self.hori_low * hori_l + (self.hori_high + 1.) * hori_h
        vert_l = self.vert_pool(hori_out) # 1,3,1,10
        vert_h = hori_out - vert_l

        vert_out = self.vert_low * vert_l + (self.vert_high + 1.) * vert_h

        return x * self.beta + vert_out * self.gamma

class LocalPoolStripAttention(nn.Module):
    def __init__(self, k, kernel=7) -> None:
        super().__init__()

        self.channel = k

        self.vert_low = nn.Parameter(torch.zeros(k, 1, 1))
        self.vert_high = nn.Parameter(torch.zeros(k, 1, 1))

        self.hori_low = nn.Parameter(torch.zeros(k, 1, 1))
        self.hori_high = nn.Parameter(torch.zeros(k, 1, 1))

        self.vert_pool = nn.AvgPool2d(kernel_size=(kernel, 1), stride=1)
        self.hori_pool = nn.AvgPool2d(kernel_size=(1, kernel), stride=1)

        pad_size = kernel // 2
        self.pad_vert = nn.ReflectionPad2d((0, 0, pad_size, pad_size))
        self.pad_hori = nn.ReflectionPad2d((pad_size, pad_size, 0, 0))

        self.gamma = nn.Parameter(torch.zeros(k,1,1))
        self.beta = nn.Parameter(torch.ones(k,1,1))

    def forward(self, x):
        hori_l = self.hori_pool(self.pad_hori(x))
        hori_h = x - hori_l

        hori_out = self.hori_low * hori_l + (self.hori_high + 1.) * hori_h

        vert_l = self.vert_pool(self.pad_vert(hori_out))
        vert_h = hori_out - vert_l

        vert_out = self.vert_low * vert_l + (self.vert_high + 1.) * vert_h

        return x * self.beta + vert_out * self.gamma

class SpecAtte(nn.Module):
    def __init__(self, k) -> None:
        super().__init__()

        self.global_att = GlobalPoolStripAttention(k)
        self.local_att_7 = LocalPoolStripAttention(k, kernel=7)
        self.local_att_11 = LocalPoolStripAttention(k, kernel=11)
        self.conv = nn.Conv2d(k, k, 1)

    def forward(self, x):
        
        global_out = self.global_att(x)
        local_7_out = self.local_att_7(x)
        local_11_out = self.local_att_11(x)

        out = global_out + local_7_out + local_11_out

        return self.conv(out)