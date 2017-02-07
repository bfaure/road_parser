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

class main_window(QWidget):

	def __init__(self):
		super(main_window,self).__init__()
		self.init_vars()
		self.init_ui()
		self.load_roads()

	def init_vars(self):
		pass

	def init_ui(self):
		self.roadmap = road_system()
		self.layout = QVBoxLayout(self)
		self.layout.addWidget(self.roadmap)
		self.resize(1500,1000)
		self.setWindowTitle("Roadmap")

		self.menu_bar = QMenuBar(self)
		self.file_menu = self.menu_bar.addMenu("File")
		self.file_menu.addAction("Save As .grid",self.save,QKeySequence("Ctrl+S"))

		self.show()

	def save(self):
		self.roadmap.save_as_grid_file("test.grid")

	def load_roads(self):
		filename = "data/tl_2016_us_primaryroads.shp"
		roads = parse_roads(filename)
		self.roadmap.load_roads(roads)

	def save_as(self,name="test.grid"):
		print("Saving as test.grid...")



def main():
	pyqt_app = QApplication(sys.argv)
	_ = main_window()
	sys.exit(pyqt_app.exec_())

	print("Done")


if __name__ == '__main__':
	main()