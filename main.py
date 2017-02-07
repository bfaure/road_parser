import os
import sys
import shapefile

from os import listdir
from os.path import isfile,join

import shutil # for copying helpers.py to helpers.pyx
import filecmp



from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


'''
.shp - feature geometry
.shx - index of feature geometry
.dbf - tabular attribute information
.prj - coordinate system information
.shp.xml - FDGC metadata
.shp.iso.xml - ISO metadata
.shp.ea.iso.xml - ISO metadata

PAGE 63 of 2014 pdf describes road shapefiles...
'''

import Cython
print("Found Cython installation, copying helpers.py to helpers.pyx...")

if os.path.exists("c_helpers.pyx"):
	if filecmp.cmp("helpers.py","c_helpers.pyx")==False: # if they are not the same already
		shutil.copyfile("helpers.py","c_helpers.pyx")
else:
	shutil.copyfile("helpers.py","c_helpers.pyx")

print("Building C code (if error here change python2 to python in main.py)...")
try:
	os.system("python setup.py build_ext --inplace")
	#if ret != 0:
	#	os.system("python setup.py build_ext --inplace")
except:
	print("here")
	os.system("python setup.py build_ext --inplace")

from c_helpers import road_t, road_system, parse_roads

class drawing_path():
	def __init__(self):
		self.x_pos = []
		self.y_pos = []
	def add_point(self, x, y):
		# Adds a single point to the path
		self.x_pos.append(x)
		self.y_pos.append(y)
	def clear_path(self):
		# Clears both the x and y components of the path
		self.x_pos = []
		self.y_pos = []
	def print_path(self):
		# Outputs a represenation of the path to the terminal
		smallest_x 	= 1000
		largest_x 	= 0
		smallest_y 	= 1000
		largest_y 	= 0

		for x,y in list(zip(self.x_pos, self.y_pos)):
			if x > largest_x:
				largest_x = x
			if x < smallest_x:
				smallest_x = x
			if y > largest_y:
				largest_y = y
			if y < smallest_y:
				smallest_y = y

		translated_x = []
		translated_y = []

		for x,y in list(zip(self.x_pos, self.y_pos)):
			translated_x.append(x-smallest_x)
			translated_y.append(y-smallest_y)

		x_size = largest_x - smallest_x
		y_size = largest_y - smallest_y

		for y in range(y_size):
			line = ""
			for x in range(x_size):
				isPixel = False
				for x_coor,y_coor in list(zip(translated_x, translated_y)):
					if isPixel == False:
						if x_coor==x and y_coor==y:
							line += "X"
							isPixel = True
				if isPixel == False:
					line += "  "
			print(line)


class main_window(QWidget):

	def __init__(self):
		super(main_window,self).__init__()
		self.init_vars()
		self.init_ui()
		self.load_roads()

	def init_vars(self):
		self.drawing_zoom = False
		self.path = drawing_path()
		
	def init_ui(self):
		self.roadmap = road_system()
		self.layout = QVBoxLayout(self)
		self.layout.addWidget(self.roadmap)
		self.resize(1500,1000)
		self.setWindowTitle("Roadmap")

		self.menu_bar = QMenuBar(self)
		self.file_menu = self.menu_bar.addMenu("File")
		self.file_menu.addAction("Save As .grid",self.save,QKeySequence("Ctrl+S"))

		self.view_menu = self.menu_bar.addMenu("View")
		self.view_menu.addAction("Zoom...",self.start_zoom,QKeySequence("Ctrl+Z"))
		self.view_menu.addAction("Reset Zoom",self.reset_zoom,QKeySequence("Ctrl+R"))

		self.show()

	def clear_zoom_path(self):
		self.path.clear_path()
		self.update()

	def mousePressEvent(self, event):
		if self.drawing_zoom:
			x = event.x()
			y = event.y()
			self.path.clear_path()

			self.mouseHeld = True
			position = event.pos()
			self.path.add_point(x,y)

			self.mouseHeld = False
			return

	def paintEvent(self, event):
		painter = QPainter()
		painter.begin(self)

		last_x = 0
		last_y = 0
		for x,y in list(zip(self.path.x_pos, self.path.y_pos)):
			if last_x == 0:
				last_x = x
				last_y = y
			else:
				painter.drawLine(last_x, last_y, x, y)
				last_x = x
				last_y = y
		painter.end()

	def mouseMoveEvent(self, event):
		if self.drawing_zoom:
			x = event.x()
			y = event.y()

			if self.mouseHeld == True:

				position = event.pos()
				self.path.add_point(x,y)

				self.repaint()
				return
			else:
				return

	def mouseReleaseEvent(self, event):
		if self.drawing_zoom:
			self.drawing_zoom = False
			self.mouseHeld = False
			#self.emit(SIGNAL("send_data(PyQt_PyObject)"), self.path)
			self.roadmap.set_zoom_dimensions(self.path)
			#self.clear_zoom_path()

	def reset_zoom(self):
		self.roadmap.reset_zoom()

	def start_zoom(self):
		self.drawing_zoom = True

	def save(self):
		self.roadmap.save_as_grid_file("test.grid",10,10)

	def load_roads(self):
		filename = "data/tl_2016_us_primaryroads.shp"
		roads = parse_roads(filename)
		self.roadmap.load_roads(roads)

def main():
	pyqt_app = QApplication(sys.argv)
	_ = main_window()
	sys.exit(pyqt_app.exec_())

	print("Done")


if __name__ == '__main__':
	main()