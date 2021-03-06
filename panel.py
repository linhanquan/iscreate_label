#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# ========================================================================
# How to run these script: $ /usr/bin/python main.py
# ========================================================================

try:
    import wx
except:
    import site
    site.addsitedir("/Users/zomi/anaconda/lib/python2.7/site-packages/")
    import wx

import json
import os
import sys
import cv2
import numpy as np
from wx.lib import buttons

from core.utils import Stack
from core.framedata import get_label_data
from core.imgpprocess import SaveImage

FLOOD_VALUE = 10
THICK_VALUE = 15


class LeftPanel(wx.Panel):
    """
    The left panel object.
    # ==========================================
    # == Initialisation and Window Management ==
    # ==========================================
    """
    BMP_SIZE = 16
    BMP_BORDER = 3
    NUM_COLS = 4
    SPACING = 4
    LABEL_HINT = ["Classify Color", "Floodfill Range", "Brush Thickness"]

    def __init__(self, parent, ID, sketch, tool):
        wx.Panel.__init__(
            self, parent, ID, size=(120, 710), style=wx.RAISED_BORDER)
        print "__init__ LeftPanel"

        # Default parament
        self.sketch = sketch
        self.tool = tool

        # funtional grid
        colorGrid = self.createColorGrid(parent)

        # label grid
        colorlabel = self.createLabelText(self.LABEL_HINT[0])

        if self.tool == 'magic':
            secondlabel = self.createLabelText(self.LABEL_HINT[1])
            floodGrid = self.createFloodGrid(parent)
            self.layout(colorlabel, colorGrid, secondlabel, floodGrid)
        elif self.tool == 'brush':
            secondlabel = self.createLabelText(self.LABEL_HINT[2])
            thickGrid = self.createThickGrid(parent)
            self.layout(colorlabel, colorGrid, secondlabel, thickGrid)
        else:
            self.layout(colorlabel, colorGrid)

    def createColorGrid(self, parent):
        buttonSize = (self.BMP_SIZE + 2 * self.BMP_BORDER,
                      self.BMP_SIZE + 2 * self.BMP_BORDER)

        self.label_data = get_label_data()
        self.show_label = self.label_data[0]['cn_name']
        self.curr_label = self.label_data[0]['en_name']
        self.curr_color = self.label_data[0]['color']
        self.colorMap = {}
        self.colorButtons = {}

        colorGrid = wx.GridSizer(cols=self.NUM_COLS, hgap=4, vgap=4)
        for idx, each_label in enumerate(self.label_data):
            color_rgb = tuple(each_label['color'])
            bmp = self._MakeBitmap(color_rgb)
            b = buttons.GenBitmapToggleButton(self, -1, bmp, size=buttonSize)
            b.SetBezelWidth(1)
            b.SetUseFocusIndicator(False)
            b.SetLabel(each_label['en_name'])
            self.Bind(wx.EVT_BUTTON, self.OnSetColour, b)
            colorGrid.Add(b, 0)
            self.colorMap[b.GetId()] = idx
            self.colorButtons[idx] = b
        self.colorButtons[0].SetToggle(True)

        return colorGrid

    def createThickGrid(self, parent):
        thick_grid = wx.GridSizer(rows=1, cols=1, hgap=0, vgap=0)
        self.thick_slider = wx.Slider(
            self, -1, THICK_VALUE, 5, 40, pos=(0, 0), size=(100, -1),
            style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS)
        self.Bind(wx.EVT_SLIDER, self.OnSetThick, self.thick_slider)

        thick_grid.Add(self.thick_slider, 0)
        return thick_grid

    def createFloodGrid(self, parent):
        flood_grid = wx.GridSizer(rows=1, cols=1, hgap=0, vgap=0)
        self.slider = wx.Slider(
            self, -1, FLOOD_VALUE, 2, 30, pos=(0, 0), size=(100, -1),
            style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS)
        self.Bind(wx.EVT_SLIDER, self.OnSetFlood, self.slider)

        flood_grid.Add(self.slider, 0)
        return flood_grid

    def createLabelText(self, label_text):
        labelGrid = wx.GridSizer(1, hgap=0, vgap=0)
        labeltext = wx.StaticText(self, -1, label_text, (0, 0))
        labelGrid.Add(labeltext, 0)
        return labelGrid

    def OnSetColour(self, event):
        idx = self.colorMap[event.GetId()]
        self.curr_color = tuple(self.label_data[idx]['color'])
        self.show_label = self.label_data[idx]['cn_name']
        self.curr_label = self.label_data[idx]['en_name']

        print('Select [{}], color: {}'.format(
            self.curr_label, self.curr_color))

        if self.curr_color != self.sketch.innerPanel.color:
            # Set all the colorButtons Toggle to False
            for i in xrange(0, len(self.colorButtons)):
                self.colorButtons[i].SetToggle(False)
            self.colorButtons[idx].SetToggle(True)

        self.sketch.innerPanel.set_color(self.curr_color)

    def OnSetFlood(self, event):
        if self.tool == 'magic':
            flood_value = self.slider.GetValue()
            self.sketch.innerPanel.set_flood_value(flood_value)
            print('Set flood value: {}'.format(flood_value))

    def OnSetThick(self, event):
        if self.tool == 'brush':
            thick_value = self.thick_slider.GetValue()
            self.sketch.innerPanel.set_brushthick(thick_value)
            print('Set brush thickness: {}'.format(thick_value))

    def _MakeBitmap(self, color_rgb):
        bmp = wx.EmptyBitmap(15, 15)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)

        brush = wx.Brush(wx.Colour(color_rgb[0], color_rgb[1], color_rgb[2]))
        dc.SetBackground(brush)
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)
        return bmp

    def layout(self, *Grid):
        box = wx.BoxSizer(wx.VERTICAL)

        for grid in Grid:
            box.Add(grid, 0, wx.ALL, self.SPACING)

        self.SetSizerAndFit(box)
        box.Fit(self)


class MagicPanel(wx.Window):
    """
    The right magic panel object.
    # ==========================================
    # == Initialisation and Window Management ==
    # ==========================================
    """

    def __init__(self, parent, ID, img, mask_img, img_path, tool, win_size):

        right_size = win_size
        wx.Window.__init__(self, parent, ID, size=right_size)
        self.SetBackgroundColour("Dark Grey")

        self.win_xy = self.GetSizeTuple()
        self.innerPanel = DrawMagicPanel(
            self, ID, img, mask_img, img_path, self.win_xy)

        # Align innerPanel in Center
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        vbox = wx.BoxSizer(wx.VERTICAL)
        innerBox = wx.BoxSizer(wx.VERTICAL)
        self.innerPanel.SetSizer(innerBox)
        hbox.Add(self.innerPanel, 0, wx.ALL | wx.ALIGN_CENTER)
        vbox.Add(hbox, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        # WARNING: ware of SierSizer between SetSizerAndFit()
        self.SetSizer(vbox)
        vbox.Fit(self)

        self.Bind(wx.EVT_PAINT, self.OnMotion)

    def OnMotion(self, event):
        self.win_xy = self.GetSizeTuple()


class DrawMagicPanel(wx.Panel):
    """
    The draw magic panel object.
    # ==========================================
    # == Initialisation and Window Management ==
    # ==========================================
    """

    def __init__(self, parent, ID, img, mask_img, img_path, win_xy, color=None):
        print "__init__ DrawMagicPanel"
        # caculate scale of input image
        self.img = img
        self.mask_img = mask_img
        self.img_path = img_path
        height, width = self.img.shape[:2]
        draw_size_w = win_xy[0] - 50
        if width < draw_size_w:
            self.scale = float(draw_size_w) / float(width)
            draw_size_h = height * self.scale
        else:
            self.scale = float(draw_size_w) / float(width)
            draw_size_h = height * self.scale

        print self.scale
        self.draw_size = (int(draw_size_w), int(draw_size_h))
        wx.Panel.__init__(self, parent, ID, size=self.draw_size)
        self.SetBackgroundColour("Black")

        # Setup parament
        self.floodmin_v = FLOOD_VALUE
        self.floodmax_v = FLOOD_VALUE
        maxpqueue = 30
        maxnqueue = 10

        # setup for floodFill
        self.stack_pre = Stack()
        self.stack_nex = Stack()

        self.label_data = get_label_data()
        self.color = tuple(self.label_data[0]['color'])
        self.floodmin = (self.floodmin_v,) * 3
        self.floodmax = (self.floodmax_v,) * 3
        self.mask = np.zeros((height + 2, width + 2), np.uint8)
        self.mask[:] = 0

        # setup for drawbitmap
        self.frame = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)  # RGB
        self.bmp = wx.BitmapFromBuffer(width, height, self.frame)  # RGB

        # Bind for event
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMotion)

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self)
        dc.SetUserScale(self.scale, self.scale)
        dc.DrawBitmap(self.bmp, 0, 0)

    def OnLeftDown(self, event):
        history = {'img': np.array(self.img), 'mask': np.array(self.mask)}
        self.stack_pre.push(history)
        self.dragline = []

        self.pos = event.GetPositionTuple()
        self.pos = tuple([int(x / self.scale) for x in self.pos])
        self.CaptureMouse()

    def OnLeftUp(self, event):
        if self.HasCapture():
            coords = (0, 0) + self.pos
            self.dragline.append(coords)
            self._floodfill(coords)
            self.dragline = []
            self.ReleaseMouse()

        # self.stack_nex.push(history)
        self.Refresh()

    def OnMotion(self, event):
        if event.Dragging() and event.LeftIsDown():
            self.DragMotion(event)
        event.Skip()

    def DragMotion(self, event):
        newPos = event.GetPositionTuple()
        newPos = tuple([int(x / self.scale) for x in newPos])
        coords = self.pos + newPos
        self.dragline.append(coords)
        self._floodfill(coords)
        self.pos = newPos
        self.Refresh()
        # print "coords:", coords

    def _floodfill(self, coords):
        # begin floodfill
        point = (coords[2], coords[3])
        fill_color = (self.color[2], self.color[1], self.color[0])

        # limiting mechanism 2
        if coords[2] > self.draw_size[0] or coords[3] > self.draw_size[1] or \
                coords[0] > self.draw_size[0] or coords[1] > self.draw_size[1]:
            return

        # limiting mechanism 1
        if (self.img[point[1]][point[0]] == np.array(fill_color)).all():
            return

        # cv2.floodFill(self.mask_img, self.mask, point, fill_color,
        #               self.floodmin, self.floodmax)

        # img = np.dstack([img, np.ones((h, w), dtype="uint8") * 255])
        # cv2.addWeighted(overlay, 1.0, dst, 1.0, 0, dst)

        cv2.floodFill(self.mask_img, self.mask, point, fill_color,
                      self.floodmin, self.floodmax)
        print self.mask.shape

        cv2.imwrite("test.png", self.mask_img)
        # cv2.waitKey(0)

        # must clean the mask otherwize cannot rechange color
        # self.mask[:] = 0
        self.frame = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)  # BGR
        self.bmp.CopyFromBuffer(self.frame)

        print "[ACTION] floodfill {} with {}".format(self.pos, self.color)
        return

    def set_color(self, color_rgb):
        self.color = color_rgb

    def get_color(self):
        return self.color

    def set_flood_value(self, flood_value):
        self.floodmin = (flood_value,) * 3
        self.floodmax = (flood_value,) * 3

    def get_pre(self):
        # Mark: canot used the self.img save into Stack() because the numpy
        # is store in the memory, so we should deep copy the numpy like:
        ## B = np.array(A)
        if not self.stack_pre.is_empty():
            history = self.stack_pre.pop()
            self.img = np.array(history['img'])
            del self.mask
            self.mask = np.array(history['mask'])
            self.frame = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)
            self.bmp.CopyFromBuffer(self.frame)
            self.Refresh()
            self.Update()

    def GetNext(self):
        if not self.stack_nex.is_empty():
            history = self.stack_nex.pop()
            self.img = np.array(history['img'])
            self.mask = np.array(history['mask'])
            self.frame = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)
            self.bmp.CopyFromBuffer(self.frame)
            self.Refresh()
            self.Update()

    def next_iamge(self, img, img_path):
        del self.img
        del self.frame
        del self.bmp
        self.img_path = img_path
        self.img = np.array(img)
        height, width = self.img.shape[:2]
        self.mask = np.zeros((height + 2, width + 2), np.uint8)
        self.frame = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)  # RGB
        self.bmp = wx.BitmapFromBuffer(width, height, self.frame)  # RGB
        self.Refresh()
        self.Update()

    def save_image(self):
        # self.stack_pre.clean()
        # self.stack_nex.clean()
        print("[Save]")
        save = SaveImage(self.img, self.img_path)
        self.Refresh()
        self.Update()


class BrushPanel(wx.Window):
    """
    The right brush panel object.
    # ==========================================
    # == Initialisation and Window Management ==
    # ==========================================
    """

    def __init__(self, parent, ID, img, img_path, tool):
        default_size = (988, 711)
        wx.Window.__init__(self, parent, ID, size=default_size)
        self.SetBackgroundColour("Black")

        self.img = img
        self.ID = ID
        self.win_xy = self.GetSizeTuple()
        self.innerPanel = DrawBrushPanel(
            self, ID, self.img, img_path, self.win_xy)

        # Align innerPanel in Center
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        vbox = wx.BoxSizer(wx.VERTICAL)
        innerBox = wx.BoxSizer(wx.VERTICAL)
        self.innerPanel.SetSizer(innerBox)
        hbox.Add(self.innerPanel, 0, wx.ALL | wx.ALIGN_CENTER)
        vbox.Add(hbox, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        self.SetSizer(vbox)
        vbox.Fit(self)


class DrawBrushPanel(wx.Panel):
    """
    The draw brush panel object.
    # ==========================================
    # == Initialisation and Window Management ==
    # ==========================================

    test by experience cannot used opencv cv2.circle and cv2.line too slow
    """

    def __init__(self, parent, ID, img, img_path, win_xy, color=None):
        # caculate scale of input image
        self.img = img
        self.img_path = img_path
        height, width = self.img.shape[:2]
        draw_size_w = win_xy[0] - 50
        if width < draw_size_w:
            self.scale = float(draw_size_w) / float(width)
            draw_size_h = height * self.scale
        else:
            self.scale = float(draw_size_w) / float(width)
            draw_size_h = height * self.scale

        print "brush scale:", self.scale
        self.draw_size = (int(draw_size_w), int(draw_size_h))
        wx.Panel.__init__(self, parent, ID, size=self.draw_size)
        self.SetBackgroundColour("White")

        # Setup parament
        self.thickness = 10
        self.color = color
        self.pen = wx.Pen(self.color, self.thickness, wx.SOLID)
        self.lines = []
        self.curLine = []
        self.pos = (0, 0)
        maxpqueue = 20
        maxnqueue = 10
        self.stack_pre = Stack()
        self.stack_nex = Stack()
        self.label_data = get_label_data()

        # change image into wxpython bitmap
        self.img = cv2.resize(self.img, self.draw_size)
        self.frame = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)
        image = wx.EmptyImage(draw_size_w, draw_size_h)
        image.SetData(self.frame.tostring())
        self.bmp = image.ConvertToBitmap()
        self.init_buffer()
        # self.bmp = wx.BitmapFromBuffer(width, height, self.self.frame)

        # Bind for event
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_PAINT, self.on_paint)

    def init_buffer(self):
        dc = wx.BufferedDC(None, self.bmp)

    def get_line_data(self):
        return self.lines[:]

    def set_lines_data(self):
        self.lines = lines[:]
        self.init_buffer()
        self.Refresh()

    def on_left_down(self, event):
        self.curLine = []
        self.pos = event.GetPositionTuple()
        self.CaptureMouse()

    def on_left_up(self, event):
        if self.HasCapture():
            # Record lines action
            self.lines.append((self.color, self.thickness, self.curLine))
            self.curLine = []

            self.ReleaseMouse()

    def on_motion(self, event):
        if event.Dragging() and event.LeftIsDown():
            dc = wx.BufferedDC(wx.ClientDC(self), self.bmp)
            self.draw_motion(dc, event)
            # self.bmp.SaveFile("bit.bmp", wx.BITMAP_TYPE_BMP)
            # change self.bmp into numpy
            self.img = self._change2numpy(self.bmp)
            print "[ACTION] brush {} with {}".format(self.pos, self.color)
        event.Skip()

        return

    def draw_motion(self, dc, event):
        dc.SetPen(self.pen)
        newPos = event.GetPositionTuple()
        coords = self.pos + newPos
        self.curLine.append(coords)
        dc.DrawLine(*coords)
        self.pos = newPos

    def on_paint(self, event):
        dc = wx.BufferedPaintDC(self, self.bmp)

    def set_color(self, color):
        self.color = color
        self.pen = wx.Pen(self.color, self.thickness, wx.SOLID)

    def get_color(self):
        return self.color

    def _change2numpy(self, bitmap):
        img = wx.ImageFromBitmap(bitmap)
        arr = np.frombuffer(img.GetDataBuffer(), dtype='uint8')
        img2 = np.reshape(
            arr, (bitmap.GetHeight(), bitmap.GetWidth(), 3))  # RGB
        return cv2.cvtColor(img2, cv2.COLOR_BGR2RGB)  # BGR

    def set_brushthick(self, num):
        self.thickness = num
        self.pen = wx.Pen(self.color, self.thickness, wx.SOLID)

    def get_brushthick(self):
        return self.thickness

    def get_pre(self):
        pass

    def GetNext(self):
        pass

    def next_iamge(self, img, img_path):
        del self.img
        del self.frame
        del self.bmp
        del self.img_path

        self.img_path = img_path
        self.img = cv2.resize(img, self.draw_size)
        self.frame = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)
        image = wx.EmptyImage(self.draw_size[0], self.draw_size[1])
        image.SetData(self.frame.tostring())
        self.bmp = image.ConvertToBitmap()
        self.init_buffer()

    def save_image(self):
        pass
        # self.stack_nex.clean()
        # self.stack_pre.clean()
        # print("[Save] Saving image...")
        # save = SaveImage(self.img, self.img_path)
        # self.Refresh()
        # self.Update()
