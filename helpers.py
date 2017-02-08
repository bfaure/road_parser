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


class region:

	def __init__(self):

		self.nrows 			= -1
		self.ncols 			= -1
		self.xllcorner 		= -1
		self.yllcorner 		= -1
		self.cellsize 		= -1
		self.NODATA_value 	= -1

		self.lower_border 	= -1
		self.upper_border 	= -1
		self.left_border 	= -1
		self.right_border 	= -1

		self.src_filename 	= ""
		self.data 			= []
		self.have_data 		= False

		self.real_ncols		= -1
		self.real_nrows		= -1

	# Parses in header info & data from a .asc file
	#
	# src = filename for source .asc file
	# compression_factor = save every nth data (1 would save all data, 2 save every other, etc.)
	def parse_from_file(self, src, compression_factor=1):

		if self.have_data:
			temp = region()
			temp.parse_from_file(src,compression_factor)
			return self.stitch(temp)

		start_time = time.time()
		self.src_filename = src

		print("Parsing region topography from "+src+"...")

		file = open(src,'r')
		tags = ["ncols","nrows","xllcorner","yllcorner","cellsize","NODATA_value"]

		for tag in tags:

			line 			= file.readline()
			line_attribs 	= line.split()

			if line_attribs[0] != tag:

				print("Could not locate ["+tag+"] tag in file header, found ["+line_attribs[0]+"] instead.")
				return -1

			self.__dict__[tag] = line_attribs[1]

		self.nrows 			= int(self.nrows)
		self.ncols 			= int(self.ncols)
		self.xllcorner 		= float(self.xllcorner)
		self.yllcorner 		= float(self.yllcorner)
		self.cellsize 		= float(self.cellsize)
		self.NODATA_value	= int(self.NODATA_value)

		row_ctr = 0
		for line in file:

			row_ctr += 1
			
			# Skip the header lines
			if row_ctr <= 6:
				continue

			# Prep the x_ctr variable 
			if row_ctr == 7:
				x_ctr = -1

			x_ctr += 1
			#line = file.readline()
			if (x_ctr % compression_factor) == 0:

				new_data = []
				vals = line.split()

				y_ctr = 0
				for val in vals:
					y_ctr += 1
					if(y_ctr % compression_factor) == 0:
						new_data.append(int(val))

				self.data.append(new_data)

		self.lower_border 	= self.yllcorner
		self.upper_border 	= self.yllcorner+(self.cellsize*self.nrows)
		self.left_border 	= self.xllcorner
		self.right_border 	= self.xllcorner+(self.cellsize*self.ncols)

		self.real_nrows = self.nrows/compression_factor
		self.real_ncols = self.ncols/compression_factor

		file.close()
		print ("number of rows = "+str(len(self.data)))
		self.have_data = True
		print ("Data read & parsed in "+str(time.time()-start_time)+" seconds.")
		#print "Upper border: "+str(self.upper_border)+", Lower border: "+str(self.lower_border)
		#print "Left border: "+str(self.left_border)+", Right border: "+str(self.right_border)
		return 1

	# Returns the elevation value at the specified column and row
	def get_elev_col_row(self, column, row):

		return float(self.data[column][row])

	# Returns the elevation value closest to the input latitude & longitude
	def get_elev_lat_long(self, latitude, longitude):

		if latitude<self.lower_border or latitude>self.upper_border:
			print("Latitude ("+str(latitude)+") out of range, cannot locate elevation.")
			return -1

		if longitude<self.left_border or longitude>self.right_border:
			print ("Longitude ("+str(longitude)+") out of range, cannot locate elevation.")
			return -1

		cur_lat = self.upper_border
		
		for row in self.data:

			if cur_lat <= latitude:

				cur_long = self.left_border

				for cell in row:

					if cur_long >= longitude:

						return int(cell)

					cur_long += self.cellsize

			cur_lat -= self.cellsize

		print ("ERROR: got to end of get_elev_lat_long function.")
		return -1

	# Returns the float value of the average of all elevations in region
	def get_avg_elev(self):

		total = 0.0

		for row in self.data:
			for cell in row:
				total += float(cell)

		return float(total/(self.nrows*self.ncols))

	# Get lowest elev
	def get_lowest_elev(self):

		lowest = 10000

		for row in self.data:
			for cell in row:
				if int(cell) < lowest:
					lowest = int(cell)

		return lowest

	# Get highest elev
	def get_highest_elev(self):

		highest = 0

		for row in self.data:
			for cell in row:
				if int(cell) > highest:
					highest = int(cell)

		return highest

	# Creates surface plot of data
	def plot(self, start_x=0, start_y=0, span=-1, compression_factor=1, type="3D", elev_scale=0.1):

		start_time = time.time()

		int_data 	= []

		if start_y+span >= self.real_nrows:

			print ("ERROR: Number of rows specified greater than total in data set.")
			return

		if start_x+span >= self.real_ncols:

			print ("ERROR: Number of columns specified greater than total in data set.")
			return

		if span == -1:

			span_x = self.real_ncols - start_x
			span_y = self.real_nrows - start_y


		x_ctr = 0
		for i in xrange(start_y, start_y+span_y):
			x_ctr+=1

			if (x_ctr % compression_factor) == 0:	
				cur_row = self.data[i]
				new_row = []

				y_ctr = 0
				for j in xrange(start_x, start_x+span_x):
					y_ctr+=1

					if (y_ctr % compression_factor) == 0:
						new_row.append(int(self.data[i][j]))

				int_data.append(new_row)

		Z = np.array(int_data)

		canvas 		= scene.SceneCanvas(keys='interactive',title="Terrain Map")
		view 		= canvas.central_widget.add_view()

		if type == "3D":
			#view.camera = scene.PerspectiveCamera(mode='ortho',fov=60.0)
			view.camera = scene.TurntableCamera(up='z',center=(span_y*0.5/compression_factor,span_x*0.5/compression_factor,0))
		if type == "2D":	
			view.camera = scene.PanZoomCamera(up='z')

		# Black background, no paning, blue graph
		p1 = scene.visuals.SurfacePlot(z=Z, color=(0.5, 0.5, 1, 1), shading='smooth')

		p1.transform = scene.transforms.AffineTransform()
		#p1.transform.scale([1/49., 1/49., 0.02])
		#p1.transform.translate([-0.5, -0.5, 0])
		p1.transform.scale([1, 1, elev_scale])
		p1.transform.translate([0, 0, 0])

		view.add(p1)
		canvas.show()

		total_time = time.time()-start_time
		time_per_data = total_time/(span_x*span_y)
		print ("Surface plot rendered in "+str(total_time)+" seconds ("+str(time_per_data)+" seconds/point).")
		app.run()
		
	def stitch(self, o_region):

		if self.have_data==False:

			self.data = o_region.data
			self.nrows = o_region.nrows
			self.ncols = o_region.ncols
			self.real_ncols = o_region.real_ncols
			self.real_nrows = o_region.real_nrows
			self.lower_border = o_region.lower_border
			self.upper_border = o_region.upper_border
			self.left_border = o_region.left_border
			self.right_border = o_region.right_border
			self.xllcorner = o_region.xllcorner
			self.yllcorner = o_region.yllcorner
			self.have_data=True
			return 1

		new_data = []

		if self.xllcorner>o_region.xllcorner and abs(self.yllcorner-o_region.yllcorner)<0.1:
			# Case that the other region is directly left of this region
			#print "Concatenating new region to left of current region."
			new_data = o_region.data

			i = 0
			for my_row in self.data:
				new_data[i].extend(my_row)
				i+=1

			self.data = new_data
			self.xllcorner = o_region.xllcorner
			self.ncols += o_region.ncols
			self.real_ncols += o_region.real_ncols
			return 1

		if self.xllcorner<o_region.xllcorner and abs(self.yllcorner-o_region.yllcorner)<0.1:
			# Case that the other region is directly right of this region
			#print "Concatenating new region to right of current region."
			new_data = self.data

			i=0
			for other_row in o_region.data:
				new_data[i].extend(other_row)
				i+=1

			self.data = new_data
			self.ncols += o_region.ncols
			self.real_ncols += o_region.real_ncols
			return 1

		if self.yllcorner<o_region.yllcorner and abs(self.xllcorner-o_region.xllcorner)<0.1:
			# Case that the other region is directly above this region
			#print "Concatenating new region above current region."
			new_data = o_region.data

			for my_row in self.data:
				new_data.append(my_row)

			self.data = new_data
			self.nrows += o_region.nrows
			self.real_nrows += o_region.real_nrows
			return 1


		if self.yllcorner>o_region.yllcorner and abs(self.xllcorner-o_region.xllcorner)<0.1:
			# Case that the other region is directly below this region
			#print "Concatenating new region below current region."
			new_data = self.data

			for other_row in o_region.data:
				new_data.append(other_row)

			self.data = new_data
			self.nrows += o_region.nrows
			self.real_nrows += o_region.real_nrows
			return 1

		print ("ERROR: Got to end of stitch function without entering a case.")
		return -1

	def save(self, res):

		print ("inside save function, see exporting png in vispy documentation")

	def get_plot(self, start_x=0, start_y=0, span=-1, compression_factor=1, type="3D", elev_scale=0.1):

		start_time = time.time()

		int_data 	= []

		if start_y+span >= self.real_nrows:

			print ("ERROR: Number of rows specified greater than total in data set.")
			return

		if start_x+span >= self.real_ncols:

			print ("ERROR: Number of columns specified greater than total in data set.")
			return

		if span == -1:

			span_x = self.real_ncols - start_x
			span_y = self.real_nrows - start_y


		x_ctr = 0
		for i in xrange(start_y, start_y+span_y):
			x_ctr+=1

			if (x_ctr % compression_factor) == 0:	
				cur_row = self.data[i]
				new_row = []

				y_ctr = 0
				for j in xrange(start_x, start_x+span_x):
					y_ctr+=1

					if (y_ctr % compression_factor) == 0:
						new_row.append(int(self.data[i][j]))

				int_data.append(new_row)

		Z = np.array(int_data)

		canvas 		= scene.SceneCanvas(keys='interactive',title="Terrain Map")
		view 		= canvas.central_widget.add_view()

		if type == "3D":
			#view.camera = scene.PerspectiveCamera(mode='ortho',fov=60.0)
			view.camera = scene.TurntableCamera(up='z',center=(span_y*0.5/compression_factor,span_x*0.5/compression_factor,0))
		if type == "2D":	
			view.camera = scene.PanZoomCamera(up='z')

		# Black background, no paning, blue graph
		p1 = scene.visuals.SurfacePlot(z=Z, color=(0.5, 0.5, 1, 1), shading='smooth')

		p1.transform = scene.transforms.AffineTransform()
		p1.transform.scale([1, 1, elev_scale])
		p1.transform.translate([0, 0, 0])

		view.add(p1)
		return canvas


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
	
	send_long_lat_data = pyqtSignal(float,float)

	def __init__(self):
		super(road_system,self).__init__()
		self.init_vars()
		self.init_ui()

	def init_vars(self):

		self.using_elevation = True
		self.elevation_data = region()

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

		self.ui_initialized = False
		self.painter = None

		self.show_connected_roads = False
		self.is_connected = []

		self.start_translate = False
		self.started_translate = False
		self.translate_start_coordinates = [-1,-1]

		self.road_used_as_stem = None
		
	def init_ui(self):
		self.have_roads = False
		self.using_zoom_dimensions = False
		self.using_translated_dimensions = False

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
			self.trim_to_length(1)

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

		if self.using_elevation:
			self.load_elevation_data()
			self.normalize_elevation_data()

	def load_elevation_data(self):
		filename = "data/elevation/srtm_11_02.asc"

	def normalize_elevation_data(self):
		pass

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
			self.setCursor(QCursor(Qt.ArrowCursor))
			self.zoom()
		if self.start_translate and self.started_translate:
			self.translate_end_coordinates = [event.x(),event.y()]
			self.start_translate = False
			self.setCursor(QCursor(Qt.ArrowCursor))
			self.translate()

	def mousePressEvent(self,event):
		# if we are drawing the zoom rectance, save the start coordinates
		if self.drawing_zoom_rect:
			self.zoom_start_coordinates = [event.x(),event.y()]
			self.started_rectangle = True
		if self.start_translate:
			self.setCursor(QCursor(Qt.ClosedHandCursor))
			self.translate_start_coordinates = [event.x(),event.y()]
			self.started_translate = True

	def mouseMoveEvent(self,event):
		self.mouse_x = event.x()
		self.mouse_y = event.y()
		longitude,latitude = self.map_to_earth([self.mouse_x,self.mouse_y])
		self.send_long_lat_data.emit(float(str(longitude)[:10]),float(str(latitude)[:10]))
		if self.show_connected_roads: self.get_connected_roads()
		self.update()

	def translate(self):
		x_diff = self.translate_end_coordinates[0]-self.translate_start_coordinates[0]
		y_diff = self.translate_end_coordinates[1]-self.translate_start_coordinates[1]

		source = self.qpainterpaths
		if self.using_zoom_dimensions:
			source = self.qpainterpaths_zoomed

		new_roads = []

		for road in source:
			new_roads.append(road.translated(x_diff,y_diff))

		if self.using_zoom_dimensions:
			self.qpainterpaths_zoomed = new_roads
		else:
			self.qpainterpaths = new_roads

	def get_connected_roads(self):
		# gets all roads connected to the current mouse location
		
		click_rect = QRectF()
		click_rect.setCoords(self.mouse_x-1,self.mouse_y-1,self.mouse_x+2,self.mouse_y+2)

		current_roads = self.qpainterpaths
		if self.using_zoom_dimensions: current_roads = self.qpainterpaths_zoomed

		road_used_as_stem = []
		stems = [] # all roads in current selection

		# calculate all roads connected to mouse
		for road in current_roads:
			if road.intersects(click_rect): 
				stems.append(road)
				road_used_as_stem.append(True)
			else:
				road_used_as_stem.append(False)

		if self.road_used_as_stem == road_used_as_stem:
			return # if the same as last time, return

		if len(stems)==0:
			self.is_connected = []
			for road in current_roads:
				self.is_connected.append(False)
			return 

		self.road_used_as_stem = road_used_as_stem

		# attach up to level of 10
		attach_level = 0
		max_depth = 2
		last_length = -1
		while attach_level<max_depth:
			print("Attach depth: "+str(attach_level)+", stems: "+str(len(stems)),end="\r")
			attach_level+=1

			road_index = 0
			for road in current_roads:
				if road_used_as_stem[road_index]==False:
					for stem in stems:
						if road.intersects(stem):
							road_used_as_stem[road_index] = True 
							stems.append(road)
							break
				road_index+=1
			
			if last_length == len(stems):
				break

			last_length = len(stems)

		self.is_connected = [] # list of booleans
		road_index = 0
		for road in current_roads:
			connects = False
			if road_used_as_stem[road_index]:
				connects = True 

			if connects==False:
				for stem in stems:
					if road.intersects(stem):
						connects = True
						break
			if connects:
				self.is_connected.append(True)
			else:
				self.is_connected.append(False)

		print("\n")

		'''
		# calculate all roads connected to all roads connected to mouse
		for road in current_roads:
			if road.intersects(click_rect):
				self.is_connected.append(True) # in mouse region
			else:
				connects_to_stem = False
				for stem in stems:
					if road.intersects(stem):
						connects_to_stem = True
						break
				if connects_to_stem:
					self.is_connected.append(True) # connected to road
				else:
					start_of_road = road.elementAt(0)
					end_of_road = road.elementAt(road.elementCount()-1)

					start_x = start_of_road.x
					start_y = start_of_road.y
					end_x = end_of_road.x 
					end_y = end_of_road.y 

					for stem in stems:
						start_stem_x = stem.elementAt(0).x 
						start_stem_y = stem.elementAt(0).y 

						end_stem_x = stem.elementAt(stem.elementCount()-1).x 
						end_stem_y = stem.elementAt(stem.elementCount()-1).y 

						attach_margin = 20

						if abs(start_x-start_stem_x)<=attach_margin:
							if abs(start_y-start_stem_y)<=attach_margin:
								connects_to_stem = True 
								break

						if abs(start_x-end_stem_x)<=attach_margin:
							if abs(start_y-end_stem_y)<=attach_margin:
								connects_to_stem = True
								break

						if abs(end_x-start_stem_x)<=attach_margin:
							if abs(end_y-start_stem_y)<=attach_margin:
								connects_to_stem = True
								break

						if abs(end_x-end_stem_x)<=attach_margin:
							if abs(end_y-end_stem_y)<=attach_margin:
								connects_to_stem = True
								break

					if connects_to_stem:
						self.is_connected.append(True)
					else:
						self.is_connected.append(False) # not connected
			'''

	def paintEvent(self, e):
		qp = QPainter()
		qp.begin(self)
		self.drawWidget(qp)
		qp.end()

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

		if self.start_translate and self.started_translate:
			x_diff = self.mouse_x - self.translate_start_coordinates[0]
			y_diff = self.mouse_y - self.translate_start_coordinates[1]

			new_roads = []
			for road in roads:
				new_roads.append(road.translated(x_diff,y_diff))
			roads = new_roads

		#print("Rendering "+str(len(self.qpainterpaths))+" paths...")
		num_roads=0
		index = 0
		for path in roads:
			if path.elementCount()>1:
				num_roads+=1
				
				if self.show_connected_roads:
					if len(self.is_connected)==len(roads):
						if self.is_connected[index]:
							road_color = [0,0,255]
							pen = QPen(QColor(road_color[0],road_color[1],road_color[2]),3.0,Qt.SolidLine)
							qp.setPen(pen)
							qp.drawPath(path)

						else:
							road_color = [0,0,0]
							pen = QPen(QColor(road_color[0],road_color[1],road_color[2]),1.0,Qt.SolidLine)
							qp.setPen(pen)
							qp.drawPath(path)

				else:
					qp.drawPath(path)


			index+=1

		#print("Rendered "+str(num_roads)+" roads")

		self.new_roads = False 
		self.last_render_width = ui_width
		self.last_render_height = ui_height

		
		cursor_color = [65,105,255]
		if self.drawing_zoom_rect and self.started_rectangle:
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
			qp.drawRect(self.mouse_x-1,self.mouse_y-1,2,2)

	def map_to_ui(self,coordinate):
		x_run = (coordinate[0]-self.top_left_coordinate[0])/self.longitude_per_pixel
		y_run = (self.top_left_coordinate[1]-coordinate[1])/self.latitude_per_pixel
		#print(x_run,y_run)
		return [x_run,y_run]

	def map_to_earth(self,coordinate):
		if self.using_zoom_dimensions:
			x_run = (coordinate[0]*self.zoom_longitude_per_pixel)+self.zoom_top_left_coordinate[0]
			y_run = -1.0*((coordinate[1]*self.zoom_latitude_per_pixel)-self.zoom_top_left_coordinate[1])
		else:
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

		current_source = self.qpainterpaths
		if self.using_zoom_dimensions: # if already zoomed
			current_source = self.qpainterpaths_zoomed

		self.qpainterpaths_zoomed = []

		for path in current_source:
			save_path = True
			path_bounding_rect = path.boundingRect()

			if zoom_bounding_rect.intersects(path_bounding_rect):
				self.qpainterpaths_zoomed.append(path)

		self.expand_zoom_coordinates()
		self.using_zoom_dimensions = True
		print("Finished creating new zoom coordinates")
		return

	def expand_zoom_coordinates(self):
		# called after we have removed moved all paths in qpainterpath over
		# to qpainterpath_zoomed that are within the bounding rectangle of the zoom region

		# calculate overall bounding rectangle for remaining region...
		overall_bounding_rect = get_bounding_rect(self.qpainterpaths_zoomed)

		translate_x = overall_bounding_rect.left() # find distance from left edge
		translate_y = overall_bounding_rect.top() # find distance from top edge

		ui_height,ui_width = [self.size().height(),self.size().width()]

		x_expansion = ui_width / overall_bounding_rect.width()
		y_expansion = ui_height / overall_bounding_rect.height()

		#print("x offset: ",translate_x)
		#print("y offset: ",translate_y)
		#print("x_expansion: ",x_expansion)
		#print("y_expansion: ",y_expansion)

		num_expanded = 0
		num_zoomed_roads = len(self.qpainterpaths_zoomed)
		adjusted_qpainterpaths_zoomed = [] # list of qpainterpath objects
		for road in self.qpainterpaths_zoomed:
			adjusted_road = road.translated(-translate_x,-translate_y)
			
			print("Zoomed "+str(num_expanded)+" roads of "+str(num_zoomed_roads),end="\r")

			if adjusted_road.elementCount()>1:
				num_expanded+=1
				expanded_road = QPainterPath()
				expanded_road.moveTo(adjusted_road.elementAt(0).x*x_expansion,adjusted_road.elementAt(0).y*y_expansion)

				for i in range(1,adjusted_road.elementCount()):
					expanded_road.lineTo(adjusted_road.elementAt(i).x*x_expansion,adjusted_road.elementAt(i).y*y_expansion)
					expanded_road.moveTo(adjusted_road.elementAt(i).x*x_expansion,adjusted_road.elementAt(i).y*y_expansion)
				adjusted_qpainterpaths_zoomed.append(expanded_road)

		self.qpainterpaths_zoomed = adjusted_qpainterpaths_zoomed

		self.zoom_latitude_per_pixel = self.latitude_per_pixel/y_expansion
		self.zoom_longitude_per_pixel = self.longitude_per_pixel/x_expansion
		self.zoom_top_left_coordinate = self.map_to_earth([overall_bounding_rect.left(),overall_bounding_rect.top()])

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

def get_bounding_rect(paths):
	# takes in a list of qpainterpaths and returns the overall bounding rectangle
	overall_bounding_rect = QRectF()
	for road in paths:
		road_bounding_rect = road.boundingRect()
		overall_bounding_rect = overall_bounding_rect.united(road_bounding_rect)
	return overall_bounding_rect

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
