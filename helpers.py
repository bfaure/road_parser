from __future__ import print_function

import os
import sys
import shapefile


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

class road_t:
	def __init__(self,shape):

		self.bbox = shape.bbox 
		self.shapeType = shape.shapeType 
		self.parts = int(shape.parts[0])
		self.points = shape.points 

	def print_road(self):
		print("\n")
		print("bbox: ",self.bbox)
		print("shapeType: ",self.shapeType)
		print("parts: ",self.parts)
		print("points: ",self.points)
		print("\n")

class road_system(QWidget):
	def __init__(self):
		super(road_system,self).__init__()
		self.init_vars()
		self.init_ui()

	def init_vars(self):
		self.roads = []
		self.mapped_coordinates = []
		self.last_render_width = 1
		self.last_render_height = 1
		self.new_roads = False 

	def init_ui(self):
		self.have_roads = False

	def trim_to_continental(self):
		new_roads = []
		index = 0
		for road in self.roads:
			delete_it = False
			for longitude,latitude in road.points:
				if longitude<-125 or longitude>-65:
					delete_it = True
					break
				if latitude<24 or latitude>50:
					delete_it = True
					break
			if delete_it==False:
				new_roads.append(road)
		self.roads = new_roads

	def load_roads(self,roads):
		self.roads = roads

		only_continental = True 
		if only_continental:
			self.trim_to_continental()
		self.road_coordinates = self.get_road_coordinates()
		self.top_left_coordinate = self.get_top_left_coordinate()
		self.bottom_right_coordinate = self.get_bottom_right_coordinate()


		ui_height,ui_width = [self.size().height(),self.size().width()]
		latitude_per_pixel = float(abs(self.top_left_coordinate[1]-self.bottom_right_coordinate[1])/ui_height)
		longitude_per_pixel = float(abs(self.top_left_coordinate[0]-self.bottom_right_coordinate[0])/ui_width)

		self.latitude_per_pixel = latitude_per_pixel
		self.longitude_per_pixel = longitude_per_pixel

		self.map_all_to_ui()
		self.have_roads = True
		self.new_roads = True

	def get_top_left_coordinate(self):
		highest_latitude = -100000
		lowest_longitude = 100000

		for road in self.road_coordinates:
			for coordinate in road:

				if coordinate[0] < lowest_longitude:
					lowest_longitude = coordinate[0]

				if coordinate[1] > highest_latitude:
					highest_latitude = coordinate[1]

		return [lowest_longitude,highest_latitude]

	def get_bottom_right_coordinate(self):
		lowest_latitutude = 100000
		highest_longitude = -1000000

		for road in self.road_coordinates:
			for coordinate in road:
				if coordinate[0] > highest_longitude:
					highest_longitude = coordinate[0]
				if coordinate[1] < lowest_latitutude:
					lowest_latitutude = coordinate[1]
		return [highest_longitude,lowest_latitutude]

	def get_road_coordinates(self):
		coordinates = []
		for r in self.roads:
			coordinates.append(r.points)
		return coordinates

	def road_in_area(self,x,y,x_range,y_range):
		x_min = x - (x_range/2)
		x_max = x + (x_range/2)
		y_min = y - (y_range/2)
		y_max = y + (y_range/2)

		for road in self.mapped_coordinates:
			for coordinate in road:
				if coordinate[0]<=x_max and coordinate[0]>=x_min:
					if coordinate[1]<=y_max and coordinate[1]>=y_min:
						return True 
		return False 

	def save_as_grid_file(self,filename,height=100,width=160):
		print("Saving to "+filename+"...")

		f = open(filename,"w")

		f.write("s_start:("+str(0)+","+str(0)+")\n")
		f.write("s_goal:("+str(2)+","+str(2)+")\n")

		map_grid_coordinate_y = self.ui_height / height
		if map_grid_coordinate_y<1:
			map_grid_coordinate_y = 1

		map_grid_coordinate_x = self.ui_width / width
		if map_grid_coordinate_x<1:
			map_grid_coordinate_x = 1


		cell_chars = []

		for row in range(width):
			row_chars = []
			for column in range(height):
				row_chars.append('1')
			row_chars.append('\n')
			cell_chars.append(row_chars)

		y = 0
		for row in cell_chars:
			x = 0
			for cell in row:
				print("                                                                 ",end="\r")
				print("Checking ("+str(x)+","+str(y)+")...",end="\r")
				if self.road_in_area(x,y,map_grid_coordinate_x,map_grid_coordinate_y):
					cell_chars[y][x] = 'a'
					print("Checking ("+str(x)+","+str(y)+")... found a road",end="\r")
				else:
					print("Checking ("+str(x)+","+str(y)+")... found no road",end="\r")
				x+=1
			y+=1

		print("\n")

		cell_chars_str = ""
		for row in cell_chars:
			for item in row:
				cell_chars_str += item
		f.write(cell_chars_str)
		print("Finished saving to "+filename)

	def paintEvent(self, e):

		self.qp = QPainter()
		self.qp.begin(self)
		self.drawWidget(self.qp)
		self.qp.end()

	def drawWidget(self, qp):
		ui_height,ui_width = [self.size().height(),self.size().width()]
		top_left,bottom_right = self.top_left_coordinate,self.bottom_right_coordinate

		latitude_per_pixel = float(abs(top_left[1]-bottom_right[1])/ui_height)
		longitude_per_pixel = float(abs(top_left[0]-bottom_right[0])/ui_width)

		render_height = int(latitude_per_pixel*ui_height)
		render_width = int(longitude_per_pixel*ui_width)

		ui_width = render_width
		ui_height = render_height

		print(ui_height,ui_width,top_left,bottom_right,latitude_per_pixel,longitude_per_pixel)

		self.ui_height = ui_height
		self.ui_width = ui_width
		self.latitude_per_pixel = latitude_per_pixel
		self.longitude_per_pixel = longitude_per_pixel

		road_color = [0,0,0]
		pen = QPen(QColor(road_color[0],road_color[1],road_color[2]),1.0,Qt.SolidLine)
		qp.setPen(pen)
		qp.setBrush(Qt.NoBrush)

		road_ct = 0
		for road in self.mapped_coordinates:
			if len(road)>=1:
				print("Drawing a road: "+str(road_ct),end="\r")
				road_ct+=1
				last = road[0]
				for coordinate in road[1:]:
					current = coordinate
					qp.drawLine(last[0],last[1],current[0],current[1])
					last = current

		self.new_roads = False 
		self.last_render_width = ui_width
		self.last_render_height = ui_height

	def map_to_ui(self,coordinate):
		x_run = (coordinate[0]-self.top_left_coordinate[0])/self.longitude_per_pixel
		y_run = (self.top_left_coordinate[1]-coordinate[1])/self.latitude_per_pixel
		#print(x_run,y_run)
		return [x_run,y_run]

	def map_all_to_ui(self):
		self.mapped_coordinates = []
		for road in self.road_coordinates:
			current_road = []
			for coordinate in road:
				current_road.append(self.map_to_ui(coordinate))
			self.mapped_coordinates.append(current_road)

def parse_roads(filename):
	print("Parsing road data from "+filename+"...")
	f = open(filename,"rb")
	sf = shapefile.Reader(filename)
	shapes = sf.shapes()
	roads = []
	for s in shapes:
		road = road_t(s)
		roads.append(road)
	return roads 
