import tkinter as tk
from tkinter import filedialog
import tkinter.messagebox as msg
import configparser as cp
import ntpath
from PIL import Image, ImageTk
from PIL.ExifTags import TAGS
import cv2 as cv
import numpy as np
import sys, os


# Library function to detect ocelli using sift descriptor
def detect_ocelli(self,e=None):
    img_rgb = self.pil2bgr(self.img)
    img_rgb = cv.cvtColor(img_rgb, cv.COLOR_BGR2RGB)
    img_gray = cv.cvtColor(img_rgb, cv.COLOR_BGR2GRAY)
    template = self.pil2bgr(self.t_img)
    template = cv.cvtColor(template, cv.COLOR_BGR2GRAY)
    w, h = template.shape[::-1]
    methods = {
        1:cv.TM_CCOEFF_NORMED,
        2:cv.TM_CCORR_NORMED,
        3:cv.TM_SQDIFF_NORMED,
    }
    res = cv.matchTemplate(img_gray,template,methods[self.MATCH_METHOD.get()])
    loc = np.where( res >= self.MATCH_TH.get()/100)
    img_new = np.zeros_like(img_rgb)
    for pt in zip(*loc[::-1]):
        cv.circle(img_new,pt,3,(255,255,255),-1)
        cv.rectangle(img_rgb, pt, (pt[0] + w, pt[1] + h), (0,0,255), 1)
    img_new = cv.cvtColor(img_new, cv.COLOR_BGR2GRAY)
    self.bare_img = Image.fromarray(img_new)
    self.MATCH_OCELLI.set(str(int(cv.connectedComponents(img_new)[0])-1))
    self.set_image(None,Image.fromarray(img_rgb))
    pass