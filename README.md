# Dual-domain strip attention for image restoration


Yuning Cui, Alois Knoll


[![](https://img.shields.io/badge/Paper-blue.svg)](https://www.sciencedirect.com/science/article/abs/pii/S0893608023006974)


## Installation
The project is built with PyTorch 3.8, PyTorch 1.8.1. CUDA 10.2, cuDNN 7.6.5
For installing, follow these instructions:
~~~
conda install pytorch=1.8.1 torchvision=0.9.1 -c pytorch
pip install tensorboard einops scikit-image pytorch_msssim opencv-python
~~~
Install warmup scheduler:
~~~
cd pytorch-gradual-warmup-lr/
python setup.py install
cd ..
~~~


## Results (DSANet)
|Task|Dataset|PSNR|SSIM|
|----|------|-----|----|
|**Image Dehazing**|ITS|41.36|0.997|
||OTS|38.39|0.995|
||Dense-Haze|16.70|0.607|
||NH-HAZE|20.51|0.801|
||O-HAZE|25.79|0.94|
||NH-HAZE2|21.63|0.841|
||NHR|28.08|0.978|
|**Image Desnowing**|CSD|38.09|0.99|
||SRRS|31.97|0.98|
||Snow100K|33.70|0.95|


## Citation
If you find this project useful for your research, please consider citing:
~~~
@article{cui2024dual,
  title={Dual-domain strip attention for image restoration},
  author={Cui, Yuning and Knoll, Alois},
  journal={Neural Networks},
  volume={171},
  pages={429--439},
  year={2024},
  publisher={Elsevier}
}
~~~
## Contact
Should you have any question, please contact Yuning Cui.
