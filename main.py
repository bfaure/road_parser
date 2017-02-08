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

using_cython = True

if using_cython:
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

	from c_helpers import road_t,road_system,parse_roads

else:
	from helpers import road_t,road_system,parse_roads

pyqt_app = ""

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

	send_roads = pyqtSignal('PyQt_PyObject') # signal used to send road data to self.roadmap

	def __init__(self):
		super(main_window,self).__init__()
		self.init_vars()
		self.init_ui()
		self.load_roads()

	def init_vars(self):
		self.drawing_zoom = False
		self.path = drawing_path()
		self.mouse_x = 0
		self.mouse_y = 0
		
	def init_ui(self):
		self.roadmap = road_system()
		self.layout = QVBoxLayout(self)
		self.layout.addSpacing(25)

		top_bar_layout = QHBoxLayout()
		self.layout.addLayout(top_bar_layout)

		self.layout.addWidget(self.roadmap)
		self.resize(1600,1000)
		self.setWindowTitle("Roadmap")

		latitude_label = QLabel("Latitude: ",self)
		self.latitude_value = QLineEdit("",self)
		self.latitude_value.setEnabled(False)
		self.latitude_value.setFixedWidth(100)
		longitude_label = QLabel("Longitude: ",self)
		self.longitude_value = QLineEdit("",self)
		self.longitude_value.setEnabled(False)
		self.longitude_value.setFixedWidth(100)

		top_bar_layout.addWidget(longitude_label)
		top_bar_layout.addWidget(self.longitude_value)
		top_bar_layout.addSpacing(10)
		top_bar_layout.addWidget(latitude_label)
		top_bar_layout.addWidget(self.latitude_value)
		top_bar_layout.addStretch()

		self.menu_bar = QMenuBar(self)
		self.file_menu = self.menu_bar.addMenu("File")
		self.file_menu.addAction("Save As .grid",self.save,QKeySequence("Ctrl+S"))
		self.file_menu.addSeparator()
		self.file_menu.addAction("Quit",self.quit,QKeySequence("Ctrl+Q"))

		self.view_menu = self.menu_bar.addMenu("View")
		self.view_menu.addAction("Translate...",self.start_translate,QKeySequence("Ctrl+T"))
		self.view_menu.addSeparator()
		self.view_menu.addAction("Zoom...",self.start_zoom,QKeySequence("Ctrl+Z"))
		self.view_menu.addAction("Reset Zoom",self.reset_zoom,QKeySequence("Ctrl+R"))

		self.tools_menu = self.menu_bar.addMenu("Tools")
		self.tools_menu.addAction("Show Connecting Roads",self.show_connected_roads)
		self.tools_menu.addAction("Hide Connecting Roads",self.hide_connected_roads)

		self.send_roads.connect(self.roadmap.load_roads)
		self.roadmap.send_long_lat_data.connect(self.set_long_lat)

		self.menu_bar.setFixedWidth(200)
		self.show()

	def set_long_lat(self,longitude,latitude):
		self.longitude_value.setText(str(longitude)+" E" if longitude>0 else str(longitude*-1)+" W")
		self.latitude_value.setText(str(latitude)+" N" if latitude>0 else str(latitude*-1)+" S")

	def start_translate(self):
		self.roadmap.drawing_zoom_rect = False
		self.roadmap.started_translate = False
		self.roadmap.start_translate = True
		self.roadmap.setCursor(QCursor(Qt.OpenHandCursor))

	def show_connected_roads(self):
		self.roadmap.show_connected_roads = True

	def hide_connected_roads(self):
		self.roadmap.show_connected_roads = False

	def quit(self):
		pyqt_app.exit()

	def clear_zoom_path(self):
		self.path.clear_path()
		self.update()

	def reset_zoom(self):
		self.roadmap.reset_zoom()

	def start_zoom(self):
		self.drawing_zoom = True
		self.roadmap.setCursor(QCursor(Qt.CrossCursor))
		self.roadmap.start_zoom()

	def save(self):
		self.roadmap.save_as_grid_file("test.grid",10,10)

	def load_roads(self):
		print("Loading road data...")
		filename = "data/roads/tl_2016_us_primaryroads.shp"
		roads = parse_roads(filename)
		self.send_roads.emit(roads)
		#self.roadmap.load_roads(roads)

def main():
	global pyqt_app
	pyqt_app = QApplication(sys.argv)
	_ = main_window()
	sys.exit(pyqt_app.exec_())

	print("Done")


if __name__ == '__main__':
	main()