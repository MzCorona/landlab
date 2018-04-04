#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 27 10:14:52 2018

@author: margaux
"""

import numpy as np
import gc
from landlab.item_collection import ItemCollection
from math import pi


class ClastCollection(ItemCollection):
    """
    """
    def __init__(self,
                 grid,
                 clast_x=[],
                 clast_y=[],
                 clast_elev=[],
                 clast_radius=[]):
        """
        """

        # Save a reference to the grid
        self._grid = grid

        # Determine reference (closest) node for each clast
        _clast__node=[]
        _clast__node[:] = self._grid.find_nearest_node((clast_x[:], clast_y[:]))
        # Clast set size:
        self._nb_of_clast = len(_clast__node)

        # Store the input information and others in a dictionary:
        
        clast_data = {'clast__x' : clast_x,
                      'clast__y' : clast_y,
                      'clast__elev' : clast_elev,
                      'clast__node' : _clast__node,
                      'clast__radius' : clast_radius,
                      'lambda_0' : np.zeros(self._nb_of_clast),
                      'lambda_mean' : np.zeros(self._nb_of_clast),
                      'slope__WE' : np.zeros(self._nb_of_clast),
                      'slope__SN' : np.zeros(self._nb_of_clast),
                      'slope__steepest_azimuth' : np.full(self._nb_of_clast, np.NaN),
                      'slope__steepest_dip' : np.zeros(self._nb_of_clast),
                      'distance__to_exit' : np.full(self._nb_of_clast, np.NaN),
                      'target_node' : -np.ones(self._nb_of_clast, dtype=int),
                      'change_x' : np.zeros(self._nb_of_clast),
                      'change_y' : np.zeros(self._nb_of_clast),
                      'hop_length' : np.zeros(self._nb_of_clast),
                      'total_travelled_dist' : np.zeros(self._nb_of_clast)}

        # Build ItemCollection containing clast data:
        ItemCollection.__init__(self,               # necessary?
                                self._grid,
                                data=clast_data,
                                grid_element='node',
                                element_id=_clast__node)

#        ItemCollection(self._grid, 
#                       data = clast_data, 
#                       grid_element = 'node', 
#                       element_id = _clast__node)

#        super().__init__(
#                self,
#                self._grid,
#                data=clast_data,
#                grid_element='node',
#                element_id=_clast__node)

    def _neighborhood(self, clast):
        self._clast__node = self._grid.find_nearest_node((self.df.at[clast, 'clast__x'], self.df.at[clast, 'clast__y'])) # needs this to update after clast has moved
        _node = self.df.at[clast, 'clast__node']
        _grid = self._grid
        
        ### Adjacent row and col nodes
        _row_col_adjacent_nodes_at_node = self._grid.neighbors_at_node[_node]
        east_node = _row_col_adjacent_nodes_at_node[0]
        north_node = _row_col_adjacent_nodes_at_node[1]
        west_node = _row_col_adjacent_nodes_at_node[2]
        south_node = _row_col_adjacent_nodes_at_node[3]

        ### Adjacent diagonal nodes
        _diagonal_adjacent_nodes_at_node = self._grid.diagonal_adjacent_nodes_at_node[_node]
    
    
        ### Calculation of slopes: W to E and S to N, units=m/m
        self.df.at[clast, 'slope__WE'] = (_grid.at_node['topographic__elevation'][west_node]-
                  _grid.at_node['topographic__elevation'][east_node])/(2*self._grid.dx)
        
        self.df.at[clast, 'slope__SN'] =(self._grid.at_node['topographic__elevation'][south_node]-
                  self._grid.at_node['topographic__elevation'][north_node])/(2*self._grid.dy)
        
        
        ### COORDINATES OF CORNERS OF CELL
        self.x_of_corners_at_node=np.zeros((self._grid.number_of_nodes,4))
        self.y_of_corners_at_node=np.zeros((self._grid.number_of_nodes,4))
        
        for i in range(self._grid.number_of_nodes):
            self.x_of_corners_at_node[i,:]=[self._grid.node_x[i]+self._grid.dx/2, self._grid.node_x[i]-self._grid.dx/2, self._grid.node_x[i]-self._grid.dx/2, self._grid.node_x[i]+self._grid.dx/2]
            self.y_of_corners_at_node[i,:]=[self._grid.node_y[i]+self._grid.dx/2, self._grid.node_x[i]+self._grid.dx/2, self._grid.node_x[i]-self._grid.dx/2, self._grid.node_x[i]-self._grid.dx/2]
        

    ### Determination of direction and value of steepest slope (ss)
    def _move_to(self, clast):
        _node = self.df.at[clast, 'clast__node']
        _node_x = self._grid.node_x[_node]
        _node_y = self._grid.node_y[_node]
        _clast_x = self.df.at[clast, 'clast__x']
        _clast_y = self.df.at[clast, 'clast__y']
        _z_node = self._grid.at_node['topographic__elevation'][_node]
        we_slope = self.df.at[clast, 'slope__WE']
        sn_slope = self.df.at[clast, 'slope__SN']
        ### Adjacent row and col nodes
        _row_col_adjacent_nodes_at_node = self._grid.neighbors_at_node[_node]
        ### Adjacent diagonal nodes
        _diagonal_adjacent_nodes_at_node = self._grid.diagonal_adjacent_nodes_at_node[_node]

        if we_slope == 0:
            if sn_slope == 0:
                # centered slope is null, clast does not move:
                ss_dip = 0
                ss_azimuth = None
                dist_to_exit = None
                target_node = -1
    #            # OPTION2 (to develop):
    #            # clast moves to random direction, according to lambda_0:
    #            ss_azimuth = np.random.uniform(0.0, 2*pi, 1)   # pick a direction at random
    #            self.df.at[clast, 'slope__steepest_azimuth'] = ss_azimuth
    #            self.df.at[clast, 'slope__flag'] = '
    #            self.rand_length = np.random.exponential(scale=self.df.at[clast, 'lambda_0'], 1)
    #            dist_to_exit = 


            else: # SN slope is not 0, ss direction is S or N
                if sn_slope < 0: # ss direction is South
                    ss_dip = np.arctan(np.abs(sn_slope))   # dip in radians
                    ss_azimuth = np.radians(270) # South
                    dist_to_exit = _clast_y - (_node_y - (self._grid.dy/2))
                    target_node = _row_col_adjacent_nodes_at_node[3]
                else: # ss direction is North
                    ss_dip = np.arctan(np.abs(sn_slope))
                    ss_azimuth = np.radians(90) # North
                    dist_to_exit = (_node_y + (self._grid.dy/2)) - _clast_y
                    target_node = _row_col_adjacent_nodes_at_node[1]
        else: # we_slope is not 0
            if sn_slope == 0:
                if we_slope < 0: # ss direction is West
                    ss_dip = np.arctan(np.abs(we_slope))
                    ss_azimuth = np.radians(180) # West
                    dist_to_exit = _clast_x - (_node_x - (self._grid.dx/2))
                    target_node = _row_col_adjacent_nodes_at_node[2]
                else: # ss direction is East
                    ss_dip = np.arctan(np.abs(we_slope))
                    ss_azimuth = 0 # East
                    dist_to_exit = (_node_y + (self._grid.dx/2)) - _clast_x
                    target_node = _row_col_adjacent_nodes_at_node[0]
            else: # sn_slope is not 0
                ss_dip = np.sqrt(np.power(np.arctan(sn_slope), 2) + np.power(np.arctan(we_slope), 2))
                if sn_slope > 0 and we_slope > 0: # Quarter = NE
                    ss_azimuth = np.arctan(np.abs(sn_slope / we_slope))
                    corner = 0
                    clast_to_corner_azimuth = np.arctan(
                            np.abs(_clast_y - self.y_of_corners_at_node[_node, corner])/
                                   np.abs(_clast_x - self.x_of_corners_at_node[_node, corner]))
                    if ss_azimuth < clast_to_corner_azimuth: # Eigth = NE-row
                        dist_to_exit = (1 / np.cos(ss_dip)) * ((np.abs(self.x_of_corners_at_node[_node, corner] - _clast_x)) / (np.cos(ss_azimuth)))
                        target_node = _row_col_adjacent_nodes_at_node[0]
                        # Coordinates of vector clast-to-border:
                        [change_x, change_y] = [dist_to_exit / np.cos(ss_azimuth), dist_to_exit / np.sin(ss_azimuth)]
                    elif ss_azimuth > clast_to_corner_azimuth: # Eigth = NE-col
                        dist_to_exit = (1 / np.cos(ss_dip)) * ((np.abs(self.y_of_corners_at_node[_node, corner] - _clast_y)) / (np.cos(np.radians(90) - ss_azimuth)))
                        target_node = _row_col_adjacent_nodes_at_node[1]
                        [change_x, change_y] = [-dist_to_exit / np.sin(np.radians(90) - ss_azimuth), dist_to_exit / np.cos(np.radians(90) - ss_azimuth)]
                    elif ss_azimuth == clast_to_corner_azimuth: # exit direction is diagonal
                        dist_to_exit = np.sqrt(np.power(np.abs(self.x_of_corners_at_node[_node, corner] - _clast_x), 2) + np.power(np.abs(self.y_of_corners_at_node[_node, corner] - _clast_y), 2))
                        target_node = _diagonal_adjacent_nodes_at_node[0]
                        # Coordinates of vector clast-to-border:
                        [change_x, change_y] = [self.x_of_corners_at_node[_node, corner] - _clast_x, self.y_of_corners_at_node[_node, corner] - _clast_y]
                elif sn_slope > 0 and we_slope < 0: # Quarter = NW
                    ss_azimuth = np.radians(90) + np.arctan(np.abs(sn_slope / we_slope))
                    corner = 1
                    clast_to_corner_azimuth = np.radians(180) - np.arctan(
                            np.abs(_clast_y - self.y_of_corners_at_node[_node, corner])/
                                   np.abs(_clast_x - self.x_of_corners_at_node[_node, corner]))
                    if ss_azimuth < clast_to_corner_azimuth: # Eigth = NW-col
                        dist_to_exit = (1 / np.cos(ss_dip)) * ((np.abs(self.y_of_corners_at_node[_node, corner] - _clast_y)) / (np.cos(ss_azimuth - np.radians(90))))
                        [change_x, change_y] = [-dist_to_exit / np.sin(ss_azimuth - np.radians(90)), dist_to_exit / np.cos(ss_azimuth - np.radians(90))]
                        target_node = _row_col_adjacent_nodes_at_node[1]
                    elif ss_azimuth > clast_to_corner_azimuth: # Eigth = NW-row
                        dist_to_exit = (1 / np.cos(ss_dip)) * ((np.abs(self.x_of_corners_at_node[_node, corner] - _clast_x)) / (np.cos(np.radians(180) - ss_azimuth)))
                        [change_x, change_y] = [-dist_to_exit / np.cos(np.radians(180) - ss_azimuth), dist_to_exit / np.sin(np.radians(180) - ss_azimuth)]
                        target_node = _row_col_adjacent_nodes_at_node[2]
                    elif ss_azimuth == clast_to_corner_azimuth: # exit direction is diagonal
                        dist_to_exit = np.sqrt(np.power(np.abs(self.x_of_corners_at_node[_node, corner] - _clast_x), 2) + np.power(np.abs(self.y_of_corners_at_node[_node, corner] - _clast_y), 2))
                        [change_x, change_y] = [-(self.x_of_corners_at_node[_node, corner] - _clast_x), self.y_of_corners_at_node[_node, corner] - _clast_y]
                        target_node = _diagonal_adjacent_nodes_at_node[1]
    
                elif sn_slope < 0 and we_slope < 0: # Quarter = SW
                    ss_azimuth = np.radians(180) + np.arctan(np.abs(sn_slope / we_slope))
                    corner = 2
                    clast_to_corner_azimuth = np.radians(180) + np.arctan(
                            np.abs(_clast_y - self.y_of_corners_at_node[_node, corner])/
                                   np.abs(_clast_x - self.x_of_corners_at_node[_node, corner]))
                    if ss_azimuth < clast_to_corner_azimuth: # Eigth = SW-row
                        dist_to_exit = (1 / np.cos(ss_dip)) * ((np.abs(self.x_of_corners_at_node[_node, corner] - _clast_x)) / (np.cos(ss_azimuth - np.radians(180))))
                        [change_x, change_y] = [-dist_to_exit / np.cos(ss_azimuth - np.radians(180)), -dist_to_exit / np.sin(ss_azimuth - np.radians(180))]
                        target_node = _row_col_adjacent_nodes_at_node[2]
                    elif ss_azimuth > clast_to_corner_azimuth: # Eigth = SW-col
                        dist_to_exit = (1 / np.cos(ss_dip)) * ((np.abs(self.y_of_corners_at_node[_node, corner] - _clast_y)) / (np.cos(np.radians(270) - ss_azimuth)))
                        [change_x, change_y] = [-dist_to_exit / np.sin(np.radians(270) - ss_azimuth), -dist_to_exit / np.cos(np.radians(270) - ss_azimuth)]
                        target_node = _row_col_adjacent_nodes_at_node[3]
                    elif ss_azimuth == clast_to_corner_azimuth: # exit direction is diagonal
                        dist_to_exit = np.sqrt(np.power(np.abs(self.x_of_corners_at_node[_node, corner] - _clast_x), 2) + np.power(np.abs(self.y_of_corners_at_node[_node, corner] - _clast_y), 2))
                        [change_x, change_y] = [-(self.x_of_corners_at_node[_node, corner] - _clast_x), -(self.y_of_corners_at_node[_node, corner] - _clast_y)]
                        target_node = _diagonal_adjacent_nodes_at_node[2]
    
                elif sn_slope < 0 and we_slope < 0: # Quarter = SE
                    ss_azimuth = np.radians(270) + np.arctan(np.abs(sn_slope / we_slope))
                    corner = 3
                    clast_to_corner_azimuth = np.radians(360) - np.arctan(
                            np.abs(_clast_y - self.y_of_corners_at_node[_node, corner])/
                                   np.abs(_clast_x - self.x_of_corners_at_node[_node, corner]))
                    if ss_azimuth < clast_to_corner_azimuth: # Eigth = SE-col
                        dist_to_exit = (1 / np.cos(ss_dip)) * ((np.abs(self.y_of_corners_at_node[_node, corner] - _clast_y)) / (np.cos(ss_azimuth - np.radians(270))))
                        [change_x, change_y] = [dist_to_exit / np.sin(ss_azimuth - np.radians(270)), -dist_to_exit / np.cos(ss_azimuth - np.radians(270))]
                        target_node = _row_col_adjacent_nodes_at_node[3]
                    elif ss_azimuth > clast_to_corner_azimuth: # Eigth = SE-row
                        dist_to_exit = (1 / np.cos(ss_dip)) * ((np.abs(self.x_of_corners_at_node[_node, corner] - _clast_x) / (np.cos(np.radians(360) - ss_azimuth))))
                        [change_x, change_y] = [dist_to_exit / np.cos(np.radians(360) - ss_azimuth), -dist_to_exit / np.sin(np.radians(360) - ss_azimuth)]
                        target_node = _row_col_adjacent_nodes_at_node[0]
                    elif ss_azimuth == clast_to_corner_azimuth: # exit direction is diagonal
                        dist_to_exit = np.sqrt(np.power(np.abs(self.x_of_corners_at_node[_node, corner] - _clast_x), 2) + np.power(np.abs(self.y_of_corners_at_node[_node, corner] - _clast_y), 2))
                        [change_x, change_y] = [(self.x_of_corners_at_node[_node, corner] - _clast_x), -(self.y_of_corners_at_node[_node, corner] - _clast_y)]
                        target_node = _diagonal_adjacent_nodes_at_node[3]
        # Calculate lambda_mean:
        self.df.at[clast, 'lambda_0'] = (self._dt * self._kappa * self._grid.dx) / (self._Si * 2 * self.df.at[clast,'clast__radius'])
        self.df.at[clast, 'lambda_mean'] = self.df.at[clast,'lambda_0'] * (self._Si + ss_dip) / (self._Si - ss_dip)


        # Save values to dataframe:
        self.df.at[clast, 'slope__steepest_azimuth'] = ss_azimuth
        self.df.at[clast, 'slope__steepest_dip'] = ss_dip
        self.df.at[clast, 'distance__to_exit'] = dist_to_exit
        self.df.at[clast, 'target_node'] = target_node
        self.df.at[clast, 'change_x'] = change_x
        self.df.at[clast, 'change_y'] = change_y






    #def _test_leave_cell(self, clast):
    #    _node = self._clast__node[clast]
    #    _z_node = self._grid.at_node['topographic__elevation'][_node]
    #    S=ss_dip[clast]
    #    Si = self._Si
    #    _azimuth=azimuth
    #    lambda_mean = self._lambda_0[clast] * (Si + S) / (Si - S)
    #    R = np.random.rand(1)
    #
    #    if S >= Si:
    #        proba_leave_cell = 1
    #    else:
    #        proba_leave_cell = np.exp(((dist_to_exit) / np.cos(np.arctan(S)) / lambda_mean))
    #
    #    _move = np.zeros(1, dtype=bool)
    #
    #    if proba_leave_cell >= R:
    #        # Clast leaves node:
    #        _move = True
    #    else:
    #        _move = False
    #
    #    return _move
    

#    def _distance_to_exit_cell(self, clast):
#        _node = self.df.at[clast, 'clast__node']
#        _ss_azimuth = self.df.at[clast, 'slope__steepest_azimuth']
#        if _ss_azimuth == np.radians(270):   # South
#            dist_to_exit = self._clast_y - (self.node_y[_node]-(dy/2))
#            target_node = _row_col_adjacent_nodes_at_node[3]
#        elif _ss_azimuth == np.radians(90):   # North
#            dist_to_exit = (self.node_y[_node]+(dy/2)) - self._clast_y
#            target_node = _row_col_adjacent_nodes_at_node[1]
#        elif _ss_azimuth == np.radians(180):   # West
#            dist_to_exit = self._clast_x - (self.node_x[_node]-(dx/2))
#            target_node = _row_col_adjacent_nodes_at_node[2]
#        elif _ss_azimuth == 0:   # East
#            dist_to_exit = (self.node_y[_node]+(dx/2)) - self._clast_x
#            target_node = _row_col_adjacent_nodes_at_node[0]
#        elif _ss_azimuth
#
#


    def _change_cell_proba(self, clast):
        lambda_mean = self.df.at[clast, 'lambda_mean']
        dist_to_exit = self.df.at[clast, 'dist_to_exit']

        # Draw a random sample in the probability distribution of travel distances:
        self.rand_length = np.random.exponential(scale=lambda_mean, size=1)

        if self.rand_length < dist_to_exit: # clast stays in cell
            _change_cell = False
        else: # self.rand_length >= dist_to_exit: clast leaves cell
            _change_cell = True

        return _change_cell

    def _move_in_cell(self, clast):
        # clast stays in cell, move of distance rand_length along slope
        ss_azimuth = self.df.at[clast, 'slope__steepest_azimuth']
        ss_dip = self.df.at[clast, 'slope__steepest_dip']
        x_horizontal = self.rand_length * np.cos(ss_dip)
        if ss_azimuth <= np.radians(90):
            [change_x, change_y] = [x_horizontal * np.cos(ss_azimuth), x_horizontal * np.sin(ss_azimuth)]
        elif ss_azimuth <= np.radians(180):
            [change_x, change_y] = [-x_horizontal * np.cos(np.radians(180)-ss_azimuth), x_horizontal * np.sin(np.radians(180)-ss_azimuth)]
        elif ss_azimuth <= np.radians(270):
            [change_x, change_y] = [-x_horizontal * np.sin(np.radians(270)-ss_azimuth), -x_horizontal * np.cos(np.radians(270)-ss_azimuth)]
        else: # ss_azimuth <= np.radians(360)
            [change_x, change_y] = [x_horizontal * np.cos(np.radians(360)-ss_azimuth), -x_horizontal * np.sin(np.radians(360)-ss_azimuth)]
        # Update clast coordinates:
        self.df.at[clast, 'clast__x'] += change_x
        self.df.at[clast, 'clast__y'] += change_y
        #self.df.at[clast, 'change_x'] = change_x
        #self.df.at[clast, 'change_y'] = change_y


        self.df.at[clast, 'hop_length'] += self.rand_length

    def _move_out_of_cell(self, clast):
        # clast leaves cell, move of distance dist_to_exit along slope
        self.df.at[clast, 'clast__x'] += self.df.at[clast, 'change_x']
        self.df.at[clast, 'clast__y'] += self.df.at[clast, 'change_y']
        self.df.at[clast, 'hop_length'] += self.df.at[clast, 'dist_to_exit']
        self.df.at[clast, 'clast__node'] = self.df.at[clast, 'target_node']



    def phantom(self, clast):
        # When a clast reaches a boundary node, it exits the grid and is thus
        # flagged as phantom
        # To add: Also phantom when totally dissovled (radius = 0)
        clast_node = self.df.at[clast, 'clast__node']
        clast_radius = self.df.at[clast, 'clast__radius']
        boundary_nodes = self._grid.boundary_nodes
        _phantom = np.zeros(1, dtype=bool)

        if clast_node in boundary_nodes:
            _phantom = True
        elif clast_radius == 0.:
            _phantom = True
        else:
            _phantom = False

        return _phantom

    def clast_detach_proba(self, clast):
        # Test if clast is detached:
        # clast is detached if erosion is sufficient to expose its base
        clast__node = self.df.at[clast, 'clast__node']
        clast__elev = self.df.at[clast, 'clast__elev']
        topo__elev = self._grid.at_node['topographic__elevation'][clast__node]
        erosion = self._erosion__depth[clast__node]

        _detach = np.zeros(1, dtype=bool)

        if erosion >= topo__elev - clast__elev:
            _detach = True
        else:
            _detach = False

        return _detach

    def clast_solver_Exponential(self, dt=1., Si=1.2, kappa=0.0001, uplift=None, erosion_method='TLDiff'): # lambda_0=1, 

        self.df=self.DataFrame
        # Method loop: Depending on the method used to evolve the landscape,
        # get sediment influx, erosion and deposition
        self.erosion_method = erosion_method
        if self.erosion_method == 'TLDiff':
            self._erosion_rate = self._grid.at_node['sediment__erosion_rate']
            self._deposition_rate = self._grid.at_node['sediment__deposition_rate']
            self._sediment__flux_in = self._grid.at_node['sediment__flux_in']
        elif self.erosion_method == 'Space':
            from landlab.components import Space
            for obj in gc.get_objects():
                if isinstance(obj, Space):    # look for instance of Space
                    self._erosion_rate = obj.Es + obj.Er   # Works if only one instance of Space was made
                    self._deposition_rate = obj.depo_rate
                    self._sediment__flux_in = obj.qs_in
            # self.space = space_name CAN'T CALL INSTANCE FROM INPUT STRING NAME

        # Future version: multiple compo -> add fluxes?
        # Store various values that will be used
        self._kappa = kappa
        self._dt = dt
        self._erosion__depth = self._erosion_rate * self._dt
        self._deposition__thickness = self._deposition_rate * self._dt
        self._Si = Si #  slope above which particle motion continues indefinetly (not equal to critical slope of diffusion, see Furbish and Haff, 2010)
        hop_length_i = 0
#            self._lambda_0 = lambda_0

        self._lambda_0=np.zeros(self._nb_of_clast)
        for i in range(self._nb_of_clast-1):
            self._lambda_0[i] = (self._dt * self._kappa * self._grid.dx) / (self._Si * 2 * np.array(self.get_value(item_id=i,variable='clast__radius')))
#            self._lambda_0[:] += lambda_0

        # Uplift:
        if uplift is not None:
            if type(uplift) is str:
                self._uplift = self._grid.at_node[uplift]
            elif type(uplift) in (float, int):
                self._uplift = np.ones(self._grid.number_of_nodes) * (
                        float(uplift))
            elif len(uplift) == self._grid.number_of_nodes:
                self._uplift = np.array(uplift)
            else:
                raise TypeError('Supplied type of uplift is not recognized')

        for clast in range(self._nb_of_clast):   # Treat clasts one after the other
            # Get values from dataframe:
#                _x_clast_init = self.df.at[i, 'clast__x']
#                _y_clast_init = self.df.at[i, 'clast__y']
#                _z_clast_init = self.df.at[i, 'clast__y']
            # Test if clast in grid core (=not phantom)
            if ClastCollection.phantom(self, clast) == False:
                #print('not phantom')
                # Clast is in grid core
                # Test if clast is detached:
                if ClastCollection.clast_detach_proba(self, clast) == True:
                    #print('detached')
                    # Clast is detached -> update neighborhood info:
                    ClastCollection._neighborhood(self, clast)
                    ClastCollection._move_to(self, clast)
                    
                    self.df.at[clast, 'hop_length'] =0
                    self.rand_length = 0.
                    #Test if moves (leaves node):
                    if np.isnan(self.df.at[clast,'slope__steepest_azimuth']) is False: # if centered slope is not null (not on a flat)
                        while ClastCollection._change_cell_proba(self, clast) == True:
                            ClastCollection._move_out_of_cell(self,clast)
                            ########JUST FOR TESTING PURPOSE##################################
                            if self.df.at[clast, 'clast__node'] != self.df.at[clast, 'target_node']:
                                print('Error: moved to wrong node')
                            ##################################################################
                            ClastCollection._neighborhood(self, clast)
                            ClastCollection._move_to(self, clast)


                        else:
                            ClastCollection._move_in_cell(self,clast)
                    else: # if centered slope is null
                        pass   # go to next clast
                    # Update elevation:
                    self.df.at[clast, 'clast__elev'] = self._grid.at_node['topographic__elevation'][self.df.at[clast, 'clast__node']]
                    # Update total travelled distance:
                    self.df.at[clast, 'total_travelled_dist'] += self.df.at[clast, 'hop_length']
                if hasattr(self, '_uplift') is True:   # uplift clast if necessary
                    self.df.at[clast, 'clast__elev'] += self._uplift[self.df.at[clast, 'clast__node']] * self._dt
                else:
                    pass
            else: # clast is phantom, go to next clast
                # for display purpose: phantom clast has a radius of 0
                # self._clast__radius(i) = 0.
                pass
    
    
    
    
    
    
    

# add delta a little extra travelled distance  (delta) when displacing 
# the clast so that it does change cell, doesn't stay at boundary?
# but change_x, change_y calculated from dist_to_exit which is always longer
# than the horizontal distance so should be ok
# delta = np.power(10, -3)