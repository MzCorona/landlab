#!/usr/bin/env python
"""Rock uplift along a normal fault.

Landlab component that implements rock uplift by a normal fault. Note that this
component does not make any attempt to advect topography laterally.

 """

import numpy as np
from landlab import Component
from landlab.utils.decorators import use_field_name_or_array


TWO_PI = 2.0*np.pi

@use_field_name_or_array('node')
def _return_surface(grid, surface):
    """
    Private function to return the surface modfy with the normal fault.

    This function exists to take advantange of the 'use_field_name_or_array
    decorator which permits providing the surface as a field name or array.

    Parameters
    ----------
    grid : ModelGrid
    surface : str or ndarray of shape `(n_nodes, )`
    """
    return surface

class NormalFault(Component):
    """NormalFault implements relative rock motion due to a normal fault.

    The fault can have an arbitrary trace given by two points (x1, y1) and
    (x2, y2) in the `fault_trace` input parameter.

    This NormalFault component permits an arbitrary pattern of fault motion. 
    The throw rate is provided through the ``fault_throw_rate_through_time`` 
    parameter.
    """

    _name = 'NormalFault'

    #_cite_as = """ """

    _input_var_names = (
        'topographic__elevation',
    )

    _output_var_names = (
        'topographic__elevation',
    )

    _var_units = {
        'topographic__elevation': 'm',
    }

    _var_mapping = {
        'topographic__elevation': 'node',
    }

    _var_doc = {
        'topographic__elevation': 'elevation of the ground surface'
    }

    def __init__(self, grid, params):
        """
        Instantiation of a NormalFault.

        Parameters
        --------
        grid : ModelGrid
        faulted_surface : str or ndarray of shape `(n_nodes, )`
            Surface that is modified by the NormalFault component. Can be a
            field name or array. Default value is `topographic__elevation`.
        fault_throw_rate_through_time : dict
            Dictionary that specifies the time varying throw rate on the fault.
            Expected format is:           
            ``fault_throw_rate_through_time = {time: array, rate: array}
        fault_dip_angle : float
            Dip angle of the fault in degrees.
        fault_trace : dictionary
            Dictionary that specifies the coordinates of two locations on the
            fault trace. Expected format is
            ``fault_trace_dict = {x1: float, y1: float, x2: float, y2: float}``
            where the vector from ``(x1, y1)`` to ``(x2, y2)`` defines the
            strike of the fault trace. The orientation of the fault dip relative
            to the strike follows the right hand rule.
        include_boundaries : boolean, optional
            Flag to indicate if model grid boundaries should be uplifted. If
            set to ``True`` uplifted model grid boundaries will be set to the
            average value of their upstream nodes. Default value is False

         Examples
         --------

         Create a grid on which we will run the normal fault.

         >>> from landlab import RasterModelGrid
         >>> from landlab.components import NormalFault
         >>> grid = RasterModelGrid((5, 4))


        """
        # call the class Normal Fault inherits from
        super(NormalFault, self).__init__(grid)
        
        # save a reference to the grid
        self._grid = grid

        # get the surface to be faulted
        surface = params.get('faulted_surface', 'topographic__elevation')
        self.z = _return_surface(grid, surface)

        # get the fault throw parameter values from the parameter dictionary
        self.throw_time = np.array(params['fault_through_rate_through_time']['time'])
        self.throw_rate = np.array(params['fault_through_rate_through_time']['rate'])
        self.fault_dip = np.deg2rad(params['fault_dip_angle'])
        self.uplift = self.throw_rate * np.sin(self.fault_dip)

        # Identify in current boundaries will be included
        self.include_boundaries = params.get('include_boundaries', False)
        
        # Instantiate record of current time. 
        self.current_time = 0.0

        # get the fault trace dictionary and use to to calculate where the 
        # faulted nodes are located. 
        
        self.fault_trace_dict = params['fault_trace']
        dx = self.fault_trace_dict['x2'] - self.fault_trace_dict['x1']
        dy = self.fault_trace_dict['y2'] - self.fault_trace_dict['y1']
        self.fault_azimuth = np.mod(np.arctan2(dy, dx), TWO_PI)
        self.fault_anti_azimuth = self.fault_azimuth + np.pi

        if dx == 0:
            self.dy_over_dx = 0.0
            self.fault_trace_y_intercept = 0.0
            self.fault_trace_x_intercept = self.fault_trace_dict['x2']
        else:
            self.dy_over_dx = dy/dx
            self.fault_trace_y_intercept = self.fault_trace_dict['y1'] - (self.dy_over_dx * self.fault_trace_dict['x1'])
            self.fault_trace_x_intercept = 0.0

        # select those nodes that are on the correct side of the node
        if self.include_boundaries:
            potential_nodes = np.arange(self._grid.size('node'))
        else:
            potential_nodes = self._grid.core_nodes

        dx_pn = (self._grid.x_of_node[potential_nodes] - self.fault_trace_x_intercept)
        dy_pn = (self._grid.y_of_node[potential_nodes] - self.fault_trace_y_intercept)

        potential_angles = np.mod(np.arctan2(dy_pn, dx_pn), TWO_PI)

        if self.fault_anti_azimuth <= TWO_PI:
            faulted_node_ids = potential_nodes[((potential_angles>self.fault_azimuth) &
                                                  (potential_angles <= (self.fault_anti_azimuth)))]
        else:
            faulted_node_ids = potential_nodes[((potential_angles>self.fault_azimuth) |
                                                  (potential_angles <= np.mod(self.fault_anti_azimuth, TWO_PI)))]

        # faulted_nodes
        self.faulted_nodes = np.zeros(self._grid.size('node'), dtype=bool)
        self.faulted_nodes[faulted_node_ids] = True

    def run_one_step(self, dt):
        """Run_one_step method for NormalFault.

        Parameters
        ----------
        dt : float
            Time increment used to advance the NormalFault component.

        """
        # save z before uplift
        z_before_uplift = self.z.copy()

        # calculate the current uplift rate
        current_uplift_rate = np.interp(self.current_time, self.throw_time, self.throw_rate)
        
        # uplift the faulted_nodes
        self.z[self.faulted_nodes] += current_uplift_rate * dt
           
        # if faulted nodes includes boundaries we must do some extra work because
        # landlab components will typically not erode these boundaries. This means
        # they will be uplifted but not eroded. 
        
        if self.include_boundaries:
            
            #  here our goal is to set faulted boundaries to average of open 
            # node faulted neighbors

            # create boolean of the faulted boundary nodes
            faulted_boundaries = self.faulted_nodes.copy()
            faulted_boundaries[self._grid.core_nodes] = False

            core_nodes = np.zeros(self._grid.size('node'), dtype=bool)
            core_nodes[self._grid.core_nodes] = True

            neighbor_is_core = core_nodes[self._grid.neighbors_at_node]
            neighbor_is_faulted = self.faulted_nodes[self._grid.neighbors_at_node]

            neighbor_for_averaging = neighbor_is_faulted&neighbor_is_core

            # Identify nodes that have at least one adjacent node that is both
            # faulted and not a boundary node.
            # average the pre-uplift topography on those adjacent nodes and assign
            # to the boundary node.
            # here we use the pre-uplift elevation because other steps in the model
            # may diminish this topography.

            averaged = neighbor_for_averaging[faulted_boundaries].sum(axis=1) == 1
            if any(averaged):
                averaged_nodes = np.where(faulted_boundaries)[0][np.where(averaged)[0]]
                elevations_to_average =  z_before_uplift[self._grid.neighbors_at_node]
                elevations_to_average[self._grid.neighbors_at_node == -1] = np.nan
                elevations_to_average[neighbor_for_averaging == False] = np.nan
                self.z[averaged_nodes] = np.nanmean(elevations_to_average[averaged_nodes], axis=1)

            # identify any boundary nodes that are not being averaged. This will
            # happen at the corners on RasterModelGrids. Average over adjacent
            # nodes that are faulted. These nodes will be boundary nodes.
            # here we use the current topography as we will have just updated the
            # adjacent nodes in the prior block.
            if any(averaged == False):
                un_averaged_nodes = np.where(faulted_boundaries)[0][np.where(averaged == False)[0]]
                elevations_to_average =  self.z[self._grid.neighbors_at_node]
                elevations_to_average[self._grid.neighbors_at_node == -1] = np.nan
                elevations_to_average[neighbor_is_faulted == False] = np.nan
                self.z[un_averaged_nodes] = np.nanmean(elevations_to_average[un_averaged_nodes], axis=1)

        # increment time
        self.current_time += dt
