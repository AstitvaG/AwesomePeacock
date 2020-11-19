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
from skimage import color
from skimage.transform import hough_circle, hough_circle_peaks
from skimage.feature import canny
from skimage.draw import circle_perimeter
from skimage.util import img_as_ubyte


class Detector(tk.Tk):

    def __init__(self):
        '''
        Constructor Function for the window
        Renders all the content and asks user to select image
        '''
        super().__init__()

        self.title("Peacock feather ocelli detection")
        self.geometry("1200x900")

        self.active_ini = ""
        self.active_ini_filename = ""
        self.ini_elements = {}


        self.left_frame = tk.Frame(self, width=800, bg="grey")
        self.left_frame.pack_propagate(0)

        self.right_frame = tk.Frame(self, width=400, bg="lightgrey")
        self.right_frame.pack_propagate(0)

        self.METHOD_TYPE = tk.StringVar(self)
        self.METHOD_TYPE.set("Detection Using Template Matching")

        self.method_label = tk.OptionMenu(self, self.METHOD_TYPE, "Detection Using Template Matching", "Detection Using Hough Transform", command=self.update_method)
        self.method_label.pack(side=tk.TOP, expand=1, fill=tk.X, anchor="n")

        self.select_template = False
        self.started_selecting = False

        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH)
        self.right_frame.pack(side=tk.LEFT, expand=1, fill=tk.BOTH)

        self.right_frame.bind("<Configure>", self.frame_height)


        self.template = ImageTk.PhotoImage(Image.open("feather1.jpg").resize((100, 100),Image.ANTIALIAS))
        self.t_img = Image.open("feather1.jpg")

        self.message = None
        self.rectangle = None
        self.canvas_image = None
        self.template_canvas_image = None
        self.canvas_message = None
        self.files = []
        self.box = [0, 0, 0, 0]
        self.ratio = 1.0
        self.canvas = tk.Canvas(self.left_frame,
                                    highlightthickness=0,
                                    bd=0)
        self.template_canvas = tk.Canvas(self.right_frame,
                                    highlightthickness=0,
                                    bd=0)

        self.bind("<Button-1>", self.__on_mouse_down)
        self.bind("<ButtonRelease-1>", self.__on_mouse_release)
        self.bind("<B1-Motion>", self.__on_mouse_move)

        # self.bind("<Control-n>", self.file_new)
        self.bind("<Control-o>", self.file_open)
        self.bind('<Return>', self.detect_ocelli)
        # self.bind("<Control-s>", self.file_save)


        self.MATCH_METHOD = tk.IntVar()
        self.MATCH_METHOD.set(1)
        self.MATCH_TH = tk.IntVar()
        self.MATCH_TH.set(50)
        self.MATCH_MIN_TH = tk.IntVar()
        self.MATCH_MIN_TH.set(50)
        self.MATCH_MAX_TH = tk.IntVar()
        self.MATCH_MAX_TH.set(50)
        self.OTSU_THRES = tk.IntVar()
        self.OTSU_THRES.set(-1)
        self.SIGMA = tk.StringVar(self)
        self.SIGMA.set("2.5")
        self.MIN_RAD = tk.IntVar()
        self.MIN_RAD.set(5)
        self.MAX_RAD = tk.IntVar()
        self.MAX_RAD.set(10)
        self.MIN_DIST = tk.IntVar()
        self.MIN_DIST.set(23)
        self.MATCH_OCELLI = tk.StringVar(self)
        self.MATCH_OCELLI.set("0")
        self.IMAGE_TYPE = tk.IntVar()
        self.IMAGE_TYPE.set(1)
        self.file_open()

    def set_image(self, filename=None, rec_img=None):
        '''
        Sets the image in the display view
        Args:
            filename: Loction of file to be opened
            rec_img: PIL image
        '''
        if filename == None and rec_img == None:
            return
        if rec_img==None:
            self.filename = filename
            try:
                self.img = Image.open(filename)
                rec_img = Image.open(filename)
            except IOError:
                print('Ignore: ' + filename + ' cannot be opened as an image')
                return False

        ratio = float(rec_img.size[1]) / rec_img.size[0]
        if rec_img.size[0] > 800:
            self.scale = rec_img.size[0] / 800
        elif rec_img.size[1] > 500:
            self.scale = rec_img.size[1] / 500
        elif rec_img.size[0] < 800 and rec_img.size[1] < 500:
            v1 = rec_img.size[0] / 800
            v2 = rec_img.size[1] / 500
            self.scale = max(v1,v2)
        else: self.scale = 1
        self.resized_img = rec_img.resize((int(rec_img.size[0] / self.scale),
                                            int(rec_img.size[1] / self.scale)),
                                            Image.ANTIALIAS)
        self.photo = ImageTk.PhotoImage(self.resized_img)
        self.canvas.delete(self.canvas_image)
        self.canvas.config(
            width=self.resized_img.size[0], height=self.resized_img.size[1])
        self.canvas_image = self.canvas.create_image(
            0, 0, anchor=tk.NW, image=self.photo)
        self.canvas.pack(expand=1)
        self.left_frame.update()
        # self.display_section_contents()

        return True

    def update_method(self,e=None):
        '''
        Updates the detection technique
        '''
        self.IMAGE_TYPE.set(1)
        self.detect_ocelli()
        self.display_section_contents()
    
    def frame_height(self, event=None):
        '''
        Handles change of frane height
        '''
        new_height = self.winfo_height()
        self.right_frame.configure(height=new_height)


    def file_open(self, event=None):
        '''
        Opens an new image file
        '''
        image_file = filedialog.askopenfilename(filetypes=[('Image files', ('.png', '.jpg', '.jpeg'))])

        if image_file:
            self.set_image(image_file)
            self.display_section_contents()
            self.detect_ocelli()

    def clear_right_frame(self):
        '''
        Clears the content of right section
        '''
        for child in self.right_frame.winfo_children():
            child.destroy()


    def start_selecting(self):
        '''
        Function to start selecting template
        '''
        self.select_template = not self.select_template
        self.selectbutton["state"]="disabled"
        self.selectbutton["text"]="Draw a square on the image"

    def display_section_contents_sift(self, event=None):
        '''
        Displays and renders the settings window for sift method
        '''

        for child in self.right_frame.winfo_children():
            child.pack_forget()
        
        new_label = tk.Label(self.right_frame, text="Number of Eyes: ", font=(None, 12), bg="black", fg="white")
        new_label.pack(fill=tk.X, side=tk.TOP, pady=(25,0))
        new_label = tk.Label(self.right_frame, textvariable=self.MATCH_OCELLI, font=(None, 12), bg="lightgrey", fg="black")
        new_label.pack(fill=tk.X, side=tk.TOP, pady=(25,25))
        

        tk.Label(self.right_frame, text="Settings", font=(None, 12), bg="black", fg="white").pack(fill=tk.X, side=tk.TOP, pady=(10,0))

        tk.Label(self.right_frame, text="Matching method (Normalized)", font=(None, 12), bg="lightgrey", fg="black").pack(fill=tk.X, side=tk.TOP, pady=(10,0))

        methods = [
            ("CCOEFF",1),
            ("CCORR",2),
            ("SQDIFF",3),
        ]

        for txt, val in methods:
            tk.Radiobutton(self.right_frame, text=txt, padx = 20, variable=self.MATCH_METHOD, value=val, bg="lightgrey", command=self.detect_ocelli).pack()

        tk.Label(self.right_frame, text="Template", font=(None, 12), bg="lightgrey", fg="black").pack(fill=tk.X, side=tk.TOP, pady=(10,0))
        
        # self.photo = ImageTk.PhotoImage(self.resized_img)
        self.template_canvas.delete(self.template_canvas_image)
        self.template_canvas.config(width=100, height=100)
        self.template_canvas_image = self.template_canvas.create_image(
            0, 0, anchor=tk.NW, image=self.template)
        self.template_canvas.pack()
        self.right_frame.update()
        
        self.selectbutton = tk.Button(self.right_frame, text="Select new", command=self.start_selecting)
        self.selectbutton.pack(side=tk.TOP, pady=(0,20))


        new_label = tk.Label(self.right_frame, text="Threshold (Percent)", font=(None, 12), bg="lightgrey", fg="black")
        new_label.pack(fill=tk.X, side=tk.TOP, pady=(10,0))
        w2 = tk.Scale(self.right_frame, from_=0, to=100, orient=tk.HORIZONTAL, bg="lightgrey", variable=self.MATCH_TH, command=self.detect_ocelli)
        # w2.set(23)
        w2.pack(fill=tk.X, side=tk.TOP, padx=(40,40), pady=(0,0))

        methods = [
            ("Detected",1),
            ("Original",2),
            ("Bare (Detected)",3),
            ("Detected (Without Noise)",4),
        ]
        new_label = tk.Label(self.right_frame, text="Image type", font=(None, 12), bg="lightgrey", fg="black")
        new_label.pack(fill=tk.X, side=tk.TOP, pady=(20,0))
        for txt, val in methods:
            tk.Radiobutton(self.right_frame, text=txt, padx = 20, variable=self.IMAGE_TYPE, value=val, bg="lightgrey", command=self.changeimage).pack()


        save_button = tk.Button(self.right_frame, text="Open New (Ctrl+O)", command=self.file_open)
        save_button.pack(side=tk.BOTTOM, pady=(0,20))

    def display_section_contents_hough(self, event=None):
        '''
        Displays and renders the settings window for hough transform
        '''

        for child in self.right_frame.winfo_children():
            child.pack_forget()
        
        new_label = tk.Label(self.right_frame, text="Number of Eyes: ", font=(None, 12), bg="black", fg="white")
        new_label.pack(fill=tk.X, side=tk.TOP, pady=(25,0))
        new_label = tk.Label(self.right_frame, textvariable=self.MATCH_OCELLI, font=(None, 12), bg="lightgrey", fg="black")
        new_label.pack(fill=tk.X, side=tk.TOP, pady=(25,25))
        

        tk.Label(self.right_frame, text="Settings", font=(None, 12), bg="black", fg="white").pack(fill=tk.X, side=tk.TOP, pady=(10,0))

        tk.Label(self.right_frame, text="Max Threshold", font=(None, 12), bg="lightgrey", fg="black").pack(fill=tk.X, side=tk.TOP, pady=(10,0))
        ini_element = tk.Spinbox(self.right_frame, from_=0, to=99999, textvariable=self.MATCH_MAX_TH, bg="white", fg="black", justify="center", command=self.detect_ocelli)
        ini_element.pack(fill=tk.X, side=tk.TOP, pady=(0,10))


        tk.Label(self.right_frame, text="Min Threshold", font=(None, 12), bg="lightgrey", fg="black").pack(fill=tk.X, side=tk.TOP, pady=(10,0))
        ini_element = tk.Spinbox(self.right_frame, from_=0, to=99999, textvariable=self.MATCH_MIN_TH, bg="white", fg="black", justify="center", command=self.detect_ocelli)
        ini_element.pack(fill=tk.X, side=tk.TOP, pady=(0,10))

        self.selectbutton = tk.Button(self.right_frame, text="Use default thresholds (Otsu)", command=self.set_th_otsu)
        self.selectbutton.pack(side=tk.TOP, pady=(0,20))

        tk.Label(self.right_frame, text="Sigma", font=(None, 12), bg="lightgrey", fg="black").pack(fill=tk.X, side=tk.TOP, pady=(10,0))
        ini_element = tk.Entry(self.right_frame, textvariable=self.SIGMA, bg="white", fg="black", justify="center")
        ini_element.pack(fill=tk.X, side=tk.TOP, pady=(0,20))

        tk.Label(self.right_frame, text="Max Radius", font=(None, 12), bg="lightgrey", fg="black").pack(fill=tk.X, side=tk.TOP, pady=(10,0))
        ini_element = tk.Spinbox(self.right_frame, from_=1, to=99999, textvariable=self.MAX_RAD, bg="white", fg="black", justify="center", command=self.detect_ocelli)
        ini_element.pack(fill=tk.X, side=tk.TOP, pady=(0,10))


        tk.Label(self.right_frame, text="Min Radius", font=(None, 12), bg="lightgrey", fg="black").pack(fill=tk.X, side=tk.TOP, pady=(10,0))
        ini_element = tk.Spinbox(self.right_frame, from_=1, to=99999, textvariable=self.MIN_RAD, bg="white", fg="black", justify="center", command=self.detect_ocelli)
        ini_element.pack(fill=tk.X, side=tk.TOP, pady=(0,10))


        tk.Label(self.right_frame, text="Min Distance", font=(None, 12), bg="lightgrey", fg="black").pack(fill=tk.X, side=tk.TOP, pady=(10,0))
        ini_element = tk.Spinbox(self.right_frame, from_=1, to=99999, textvariable=self.MIN_DIST, bg="white", fg="black", justify="center", command=self.detect_ocelli)
        ini_element.pack(fill=tk.X, side=tk.TOP, pady=(10,10))

        methods = [
            ("Detected",1),
            ("Original",2),
            ("Bare (Detected)",3),
            ("Bare (Undetected)",4),
        ]
        new_label = tk.Label(self.right_frame, text="Image type", font=(None, 12), bg="lightgrey", fg="black")
        new_label.pack(fill=tk.X, side=tk.TOP, pady=(20,0))
        for txt, val in methods:
            tk.Radiobutton(self.right_frame, text=txt, padx = 20, variable=self.IMAGE_TYPE, value=val, bg="lightgrey", command=self.changeimage).pack()


        save_button = tk.Button(self.right_frame, text="Open New (Ctrl+O)", command=self.file_open)
        save_button.pack(side=tk.BOTTOM, pady=(0,20))

    def display_section_contents(self, e = None):
        '''
        Wrapper function for displaying right section
        '''
        val = self.METHOD_TYPE.get()
        if val == "Detection Using Template Matching":
            self.display_section_contents_sift()
        else:
            self.display_section_contents_hough()

    def set_th_otsu(self):
        '''
        Function to calculate the image threshold using OTSU's method
        '''
        otsu = self.OTSU_THRES.get()
        self.MATCH_MAX_TH.set(otsu)
        self.MATCH_MIN_TH.set(otsu//2)


    def __on_mouse_down(self, event):
        '''
        Handles mouse click event
        '''
        if not self.select_template: return
        self.started_selecting = True
        self.box[0], self.box[1] = event.x, event.y
        self.box[2], self.box[3] = event.x, event.y
        print("top left coordinates: %s/%s" % (event.x, event.y))



    def __on_mouse_release(self, event):
        '''
        Handles mouse release event
        '''
        if not self.select_template or not self.started_selecting: return
        self.started_selecting = False
        self.select_template = False
        print("bottom_right coordinates: %s/%s" % (self.box[2], self.box[3]))
        img = self.__crop_image()
        if img:
            self.template = ImageTk.PhotoImage(img.resize((100, 100),Image.ANTIALIAS))
            self.t_img = img
            self.display_section_contents()
        self.detect_ocelli()
        self.selectbutton["state"]="normal"
        self.selectbutton["text"]="Select new"
        self.canvas.delete(self.rectangle)

    def __crop_image(self):
        '''
        Fuunction to crop image and get the selected template
        '''
        box = (self.box[0] * self.scale,
               self.box[1] * self.scale,
               self.box[2] * self.scale,
               self.box[3] * self.scale)
        try:
            cropped = self.img.crop(box)
            if cropped.size[0] == 0 and cropped.size[1] == 0:
                raise SystemError('no size')
            return cropped
        except SystemError as e:
            pass

    def pil2bgr(self,img):
        '''
        Converts PIL image to OpenCV format bgr image
        '''
        img_rgb = np.array(img)
        return img_rgb[:, :, ::-1].copy() 
        

    def detect_ocelli_template_matching(self,e=None):
        '''
        Detects ocelli using template matching
            -> Firstly matches template using 'cv.matchTemplate'
            -> Then finds the number of connected components to count ocelli
            -> Then draws rectange over the detected areas
        '''
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
        self.bare_img_other = np.copy(img_rgb)
        for pt in zip(*loc[::-1]):
            cv.circle(img_new,pt,3,(255,255,255),-1)
            cv.rectangle(img_rgb, pt, (pt[0] + w, pt[1] + h), (0,0,255), 1)
        img_new = cv.cvtColor(img_new, cv.COLOR_BGR2GRAY)
        self.bare_img = Image.fromarray(img_new)
        conn_comp = cv.connectedComponentsWithStats(img_new)
        stats = conn_comp[2]
        for i in range(conn_comp[0]):
            if stats[i,cv.CC_STAT_WIDTH]>img_rgb.shape[1]*2//3 or stats[i,cv.CC_STAT_HEIGHT]>img_rgb.shape[0]*2//3:
                continue
            cv.rectangle(self.bare_img_other, (stats[i,cv.CC_STAT_LEFT],stats[i,cv.CC_STAT_TOP]) , (stats[i,cv.CC_STAT_LEFT]+w,stats[i,cv.CC_STAT_TOP]+h), (0,0,255), 1)
        self.bare_img_other = Image.fromarray(self.bare_img_other)
        self.MATCH_OCELLI.set(str(int(conn_comp[0])-1))
        return Image.fromarray(img_rgb)

    def detect_ocelli_hough_transform(self,e=None):
        '''
        Detects ocelli using circular hough transform
            -> Firstly Edge detection using Canny Detector
            -> Then uses circular hough transform to detect circles
            -> Then draws the detected circles on the image
        '''
        img_rgb = self.pil2bgr(self.img)
        img_rgb = cv.cvtColor(img_rgb, cv.COLOR_BGR2RGB)
        img_gray = cv.cvtColor(img_rgb, cv.COLOR_BGR2GRAY)

        high_thresh, thresh_im = cv.threshold(img_gray, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
        if self.OTSU_THRES.get()==-1:
            self.OTSU_THRES.set(high_thresh)
            self.MATCH_MAX_TH.set(high_thresh)
            self.MATCH_MIN_TH.set(high_thresh//2)

        self.bare_img = img_as_ubyte(img_gray)
        self.bare_img = canny(self.bare_img, sigma=float(self.SIGMA.get()), low_threshold=self.MATCH_MIN_TH.get(), high_threshold=self.MATCH_MAX_TH.get())

        hough_radii = np.arange(self.MIN_RAD.get(), self.MAX_RAD.get(), 1)
        hough_res = hough_circle(self.bare_img, hough_radii)

        accums, cx, cy, radii = hough_circle_peaks(
            hough_res, hough_radii, min_xdistance=self.MIN_DIST.get(), min_ydistance=self.MIN_DIST.get())

        self.MATCH_OCELLI.set(cx.shape[0])

        self.bare_img_other = Image.fromarray(self.bare_img)
        self.bare_img = cv.cvtColor(self.bare_img.astype('uint8')*255,cv.COLOR_GRAY2RGB)
        # Draw them on the image
        for center_y, center_x, radius in zip(cy, cx, radii):
            circy, circx = circle_perimeter(center_y, center_x, radius,
                                            shape=img_rgb.shape)
            img_rgb[circy, circx] = (0, 0, 255)
            self.bare_img[circy, circx] = (0, 0, 255)
        self.bare_img = Image.fromarray(self.bare_img)
        return Image.fromarray(img_rgb)

    def detect_ocelli(self,e=None):
        '''
        Wrapper function for detecting ocelli
        '''
        val = self.METHOD_TYPE.get()
        img = None
        if val == "Detection Using Template Matching":
            img = self.detect_ocelli_template_matching()
        else:
            img = self.detect_ocelli_hough_transform()
        val = self.IMAGE_TYPE.get()
        if val!=1:
            self.changeimage()
        else:
            self.set_image(None,img)
    
    def changeimage(self):
        '''
        Changes the type of image to be displayed
        '''
        val = self.IMAGE_TYPE.get()
        if val==1:
            self.detect_ocelli()
        elif val==2:
            self.set_image(None,self.img)
        elif val==3:
            self.set_image(None,self.bare_img)
        else:
            self.set_image(None,self.bare_img_other)


    def __fix_ratio_point(self, px, py):
        '''
        Makes sure that the box selected is of square shape
        '''
        dx = px - self.box[0]
        dy = py - self.box[1]
        if min((dy / self.ratio), dx) == dx:
            dy = int(dx * self.ratio)
        else:
            dx = int(dy / self.ratio)
        return self.box[0] + dx, self.box[1] + dy

    def __on_mouse_move(self, event):
        '''
        Function called when selecting image
        '''
        if not self.select_template or not self.started_selecting: return
        self.box[2], self.box[3] = self.__fix_ratio_point(event.x, event.y)
        self.__refresh_rectangle()

    
    def __refresh_rectangle(self):
        '''
        Renders the drawn rectangle over the image
        '''
        self.canvas.delete(self.rectangle)
        self.rectangle = self.canvas.create_rectangle(
            self.box[0], self.box[1], self.box[2], self.box[3],outline='red', width=3)

if __name__ == "__main__":
    detector = Detector()
    detector.mainloop()
