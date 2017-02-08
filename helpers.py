from __future__ import print_function

import os
import sys
import shapefile
import time

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

		self.mouse_x = 0
		self.mouse_y = 0

		self.drawing_zoom_rect = False
		self.started_rectangle = False
		self.zoom_start_coordinates = [-1,-1]
		self.zoom_end_coordinates = [-1,-1]
		

	def init_ui(self):
		self.have_roads = False
		self.using_zoom_dimensions = False

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

	def trim_to_length(self,length):
		new_roads = []
		index = 0
		for road in self.roads:
			delete_it = False
			if len(road.points)<length:
				delete_it = True
			if delete_it==False:
				new_roads.append(road)
		self.roads = new_roads

	def load_roads(self,roads):
		self.roads = roads

		only_continental = True 
		if only_continental:
			self.trim_to_continental()

		trim_roads = False
		if trim_roads:
			self.trim_to_length(1000)

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

		self.init_qpainterpaths()

	def init_qpainterpaths(self):
		# goes through the roads in self.road_coordinates and creates a single qpainterpath for each
		self.qpainterpaths = []
		for road in self.mapped_coordinates:
			if len(road)>=1:
				temp = QPainterPath()
				temp.moveTo(road[0][0],road[0][1])
				for coordinate in road[1:]:
					temp.lineTo(coordinate[0],coordinate[1])
					temp.moveTo(coordinate[0],coordinate[1])

				self.qpainterpaths.append(temp)

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

		print("X mapping: "+str(map_grid_coordinate_x)+", Y mapping: "+str(map_grid_coordinate_y))
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
				print("Checking ("+str(x)+","+str(y)+")...",end="\r")
				if self.road_in_area(x,y,map_grid_coordinate_x,map_grid_coordinate_y):
					cell_chars[y][x] = 'a'
					print("                                                                 ",end="\r")
					print("Checking ("+str(x)+","+str(y)+")... found a road",end="\r")
				else:
					print("                                                                 ",end="\r")
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

	
	def enterEvent(self,event):
		# called if the mouse cursor goes over the widget

		#self.verbose = False
		self.setMouseTracking(True)

	def leaveEvent(self,event):
		# called if the mouse cursor leaves the widget

		#self.verbose = True
		self.setMouseTracking(False)

	def mouseReleaseEvent(self,event):
		if self.drawing_zoom_rect and self.started_rectangle:
			self.zoom_end_coordinates = [event.x(),event.y()]
			self.drawing_zoom_rect = False
			self.zoom()

	def mousePressEvent(self,event):
		# if we are drawing the zoom rectance, save the start coordinates
		if self.drawing_zoom_rect:
			self.zoom_start_coordinates = [event.x(),event.y()]
			self.started_rectangle = True

	def mouseMoveEvent(self,event):

		self.mouse_x = event.x()
		self.mouse_y = event.y()
		self.update()

	def paintEvent(self, e):

		self.qp = QPainter()
		self.qp.begin(self)
		self.drawWidget(self.qp)
		self.qp.end()

	def drawWidget(self, qp):
		start_time = time.time()
		ui_height,ui_width = [self.size().height(),self.size().width()]
		top_left,bottom_right = self.top_left_coordinate,self.bottom_right_coordinate

		latitude_per_pixel = float(abs(top_left[1]-bottom_right[1])/ui_height)
		longitude_per_pixel = float(abs(top_left[0]-bottom_right[0])/ui_width)

		render_height = int(latitude_per_pixel*ui_height)
		render_width = int(longitude_per_pixel*ui_width)

		ui_width = render_width
		ui_height = render_height

		#print(ui_height,ui_width,top_left,bottom_right,latitude_per_pixel,longitude_per_pixel)

		self.ui_height = ui_height
		self.ui_width = ui_width
		self.latitude_per_pixel = latitude_per_pixel
		self.longitude_per_pixel = longitude_per_pixel

		road_color = [0,0,0]
		pen = QPen(QColor(road_color[0],road_color[1],road_color[2]),1.0,Qt.SolidLine)
		qp.setPen(pen)
		qp.setBrush(Qt.NoBrush)

		
		if self.using_zoom_dimensions:
			roads = self.qpainterpaths_zoomed
		else:
			roads = self.qpainterpaths

		#print("Rendering "+str(len(self.qpainterpaths))+" paths...")
		num_roads=0
		for path in roads:
			if path.elementCount()>1:
				num_roads+=1
				qp.drawPath(path)

		#print("Rendered "+str(num_roads)+" roads")

		self.new_roads = False 
		self.last_render_width = ui_width
		self.last_render_height = ui_height

		cursor_color = [255,255,10]
		pen = QPen(QColor(cursor_color[0],cursor_color[1],cursor_color[2]), 1, Qt.SolidLine)
		qp.setPen(pen)
		qp.setBrush(QColor(cursor_color[0],cursor_color[1],cursor_color[2]))

		if self.drawing_zoom_rect and self.started_rectangle:
			x0 = self.zoom_start_coordinates[0]
			y0 = self.zoom_start_coordinates[1]

			x_run = self.mouse_x-x0
			y_run = self.mouse_y-y0

			qp.setBrush(Qt.NoBrush)
			qp.drawRect(x0,y0,x_run,y_run)
		else:
			qp.drawRect(self.mouse_x-2,self.mouse_y-2,4,4)

		#print("Finished rendering map in "+str(time.time()-start_time)+" seconds")

	def map_to_ui(self,coordinate):
		x_run = (coordinate[0]-self.top_left_coordinate[0])/self.longitude_per_pixel
		y_run = (self.top_left_coordinate[1]-coordinate[1])/self.latitude_per_pixel
		#print(x_run,y_run)
		return [x_run,y_run]

	def map_to_earth(self,coordinate):
		x_run = (coordinate[0]*self.longitude_per_pixel)+self.top_left_coordinate[0]
		y_run = -1.0*((coordinate[1]*self.latitude_per_pixel)-self.top_left_coordinate[1])
		return [x_run,y_run]

	def reset_zoom(self):
		self.using_zoom_dimensions = False
		self.repaint()

	def start_zoom(self):
		self.drawing_zoom_rect = True
		self.started_rectangle = False

	def zoom(self):

		x0=-1 # top left of rectangle (smallest x)
		y0=-1 # top left of rectangle (smallest y)
		x1=-1 # bottom right of rectangle (largest x)
		y1=-1 # bottom right of rectangle (largest y)

		click = self.zoom_start_coordinates
		release = self.zoom_end_coordinates

		if click[0]<release[0]:
			x0 = click[0]
			x1 = release[0]
		else:
			x0 = release[0]
			x1 = click[0]

		if click[1]<release[1]:
			y0 = click[1]
			y1 = release[1]
		else:
			y0 = release[1]
			y1 = click[1]

		zoom_bounding_rect = QRectF()
		zoom_bounding_rect.setCoords(x0,y0,x1,y1)

		self.qpainterpaths_zoomed = []

		for path in self.qpainterpaths:
			save_path = True
			path_bounding_rect = path.boundingRect()

			if zoom_bounding_rect.intersects(path_bounding_rect):
				self.qpainterpaths_zoomed.append(path)

		self.expand_zoom_coordinates()
		self.using_zoom_dimensions = True
		return

	def expand_zoom_coordinates(self):

		overall_bounding_rect = QRectF()
		for road in self.qpainterpaths_zoomed:
			road_bounding_rect = road.boundingRect()
			overall_bounding_rect = overall_bounding_rect.united(road_bounding_rect)

		translate_x = overall_bounding_rect.left()
		translate_y = overall_bounding_rect.top()

		ui_height,ui_width = [self.size().height(),self.size().width()]

		x_expansion = ui_width / overall_bounding_rect.width()
		y_expansion = ui_height / overall_bounding_rect.height()

		print(translate_x,translate_y,x_expansion,y_expansion,ui_height,overall_bounding_rect.height())

		adjusted_qpainterpaths_zoomed = [] # list of qpainterpath objects
		for road in self.qpainterpaths_zoomed:
			adjusted_road = road.translated(translate_x,translate_y)
			
			if adjusted_road.elementCount()>1:
				expanded_road = QPainterPath()
				expanded_road.moveTo(adjusted_road.elementAt(0).x*x_expansion,adjusted_road.elementAt(0).y*y_expansion)

				for i in range(1,adjusted_road.elementCount()):
					expanded_road.lineTo(adjusted_road.elementAt(i).x*x_expansion,adjusted_road.elementAt(i).y*y_expansion)
					expanded_road.moveTo(adjusted_road.elementAt(i).x*x_expansion,adjusted_road.elementAt(i).y*y_expansion)
				adjusted_qpainterpaths_zoomed.append(expanded_road)

		self.qpainterpaths_zoomed = adjusted_qpainterpaths_zoomed
		print("Finished expanding zoomed coordinates, ",len(self.qpainterpaths_zoomed))

	def map_all_to_earth(self,path):
		self.unmapped_coordinates = []
		for coordinate in path:
			self.unmapped_coordinates.append(self.map_to_earth(coordinate))

	def map_all_to_ui(self):
		self.mapped_coordinates = []
		for road in self.road_coordinates:
			current_road = []
			for coordinate in road:
				current_road.append(self.map_to_ui(coordinate))
			self.mapped_coordinates.append(current_road)


def get_top_left_coordinate():
	highest_latitude = -100000
	lowest_longitude = 100000

	for road in road_coordinates:
		for coordinate in road:

			if coordinate[0] < lowest_longitude:
				lowest_longitude = coordinate[0]

			if coordinate[1] > highest_latitude:
				highest_latitude = coordinate[1]

	return [lowest_longitude,highest_latitude]

def get_bottom_right_coordinate():
	lowest_latitutude = 100000
	highest_longitude = -1000000

	for road in road_coordinates:
		for coordinate in road:
			if coordinate[0] > highest_longitude:
				highest_longitude = coordinate[0]
			if coordinate[1] < lowest_latitutude:
				lowest_latitutude = coordinate[1]
	return [highest_longitude,lowest_latitutude]


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
