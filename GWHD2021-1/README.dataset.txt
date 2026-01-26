# GWHD2021 > resize416
https://universe.roboflow.com/wei-guo/gwhd2021

Provided by a Roboflow user
License: MIT

Global Wheat Head Dataset 2021
Original article from https://doi.org/10.5281/zenodo.5092309
Support paper:
David, E., et al.,  (2021). Global Wheat Head Dataset 2021: more diversity to improve the benchmarking of wheat head localization methods. Plant Phenomics. Volume 2021, Article ID 9846158.

This is the full Global Wheat Head Dataset 2021. 

Tutorials available here: https://www.aicrowd.com/challenges/global-wheat-challenge-2021

Labels are included in csv and been modified to VoTT txt for roboflow upload
 

🕵️ Introduction

Wheat is the basis of the diet of a large part of humanity. Therefore, this cereal is widely studied by scientists to ensure food security. A tedious, yet important part of this research is the measurement of different characteristics of the plants, also known as Plant Phenotyping. Monitoring plant architectural characteristics allow the breeders to grow better varieties and the farmers to make better decisions, but this critical step is still done manually. The emergence of UAV, camera and smartphone makes in-field RGB images more available and could be a solution to manual measurement. For instance, the counting of the wheat head can be done with Deep Learning.  However, this task can be visually challenging. There is often an overlap of dense wheat plants, and the wind can blur the photographs, making identify single heads difficult. Additionally, appearances vary due to maturity, colour, genotype, and head orientation. Finally, because wheat is grown worldwide, different varieties, planting densities, patterns, and field conditions must be considered. To end manual counting, a robust algorithm must be created to address all these issues. 

💾 Dataset

The dataset is composed of more than 6000 images of 1024x1024 pixels containing 300k+ unique wheat heads, with the corresponding bounding boxes. The images come from 11 countries and covers 44 unique measurement sessions. A measurement session is a set of images acquired at the same location, during a coherent timestamp (usually a few hours), with a specific sensor. In comparison to the 2020 competition on Kaggle, it represents 4 new countries, 22 new measurements sessions, 1200 new images and 120k new wheat heads. This amount of new situations will help to reinforce the quality of the test dataset. The 2020 dataset was labelled by researchers and students from 9 institutions across 7 countries. The additional data have been labelled by Human in the Loop, an ethical AI labelling company. We hope these changes will help in finding the most robust algorithms possible!

The task is to localize the wheat head contained in each image. The goal is to obtain a model which is robust to variation in shape, illumination, sensor and locations. A set of boxes coordinates is provided for each image.

The training dataset will be the images acquired in Europe and Canada, which cover approximately 4000 images and the test dataset will be composed of the images from North America (except Canada), Asia, Oceania and Africa and covers approximately 2000 images. It represents 7 new measurements sessions available for training but 17 new measurements sessions for the test!