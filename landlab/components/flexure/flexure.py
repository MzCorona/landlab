#!/usr/bin/env python

import numpy as np

from landlab import RasterModelField, Component
from landlab.components.flexure.funcs import subside_point_loads


class FlexureComponent(Component):
    """
    Landlab component that implements a 1 and 2D lithospheric flexure
    model.

    >>> grid = RasterModelField((5, 4), (1.e4, 1.e4), (0., 0.))
    >>> flex = FlexureComponent(grid)
    >>> flex.name
    'Flexure'
    >>> sorted(flex.input_var_names)
    ['lithosphere__elevation', 'lithosphere__overlying_pressure', 'planet_surface_sediment__deposition_increment']
    >>> sorted(flex.output_var_names)
    ['lithosphere__elevation', 'lithosphere__elevation_increment']
    >>> for var in sorted(flex.grid.units): flex.grid.units[var]
    'm'
    'm'
    'Pa'
    'm'

    >>> flex.grid.get_count_of_rows()
    5
    >>> flex.grid.get_count_of_cols()
    4

    >>> np.all(flex.grid['lithosphere__elevation'] == 0.)
    True
    >>> np.all(flex.grid['lithosphere__overlying_pressure'] == 0.)
    True
    >>> flex.update()
    >>> np.all(flex.grid['lithosphere__elevation_increment'] == 0.)
    True

    >>> load = flex.grid['lithosphere__overlying_pressure']
    >>> load[4] = 1e9
    >>> dz = flex.grid['lithosphere__elevation_increment']
    >>> np.all(dz == 0.)
    True

    >>> flex.update()
    >>> np.all(flex.grid['lithosphere__elevation_increment'] == 0.)
    False
    """
    _name = 'Flexure'

    _input_var_names = set([
        'lithosphere__overlying_pressure',
        'lithosphere__elevation',
        'planet_surface_sediment__deposition_increment',
    ])
    _output_var_names = set([
        'lithosphere__elevation_increment',
        'lithosphere__elevation',
    ])

    _var_units = {
        'lithosphere__overlying_pressure': 'Pa',
        'lithosphere__elevation': 'm',
        'lithosphere__elevation_increment': 'm',
        'planet_surface_sediment__deposition_increment': 'm',
    }

    def __init__(self, grid, **kwds):
        self._eet = kwds.pop('eet', 65000.)
        self._youngs = kwds.pop('youngs', 7e10)
        self._airy = kwds.pop('airy', True)

        super(FlexureComponent, self).__init__(grid, **kwds)

        node_count = grid.get_count_of_all_nodes()

        for name in self._input_var_names - set(self.grid):
            self.grid.add_field(name, np.zeros(node_count, dtype=np.float),
                                units=self._var_units[name])

        for name in self._output_var_names - set(self.grid):
            self.grid.add_field(name, np.zeros(node_count, dtype=np.float),
                                units=self._var_units[name])

        self._last_load = self.grid['lithosphere__overlying_pressure'].copy()

    def update(self, n_procs=1):
        elevation = self.grid['lithosphere__elevation']
        load = self.grid['lithosphere__overlying_pressure']
        deflection = self.grid['lithosphere__elevation_increment']
        deposition = self.grid['planet_surface_sediment__deposition_increment']

        new_load = ((load - self._last_load) +
                    (deposition * 2650. * 9.81).flat)

        self._last_load = load.copy()

        deflection.fill(0.)

        if self._airy:
            deflection[:] = new_load / (3300. * 9.81)
        else:
            self.subside_loads(new_load, self.coords, deflection=deflection,
                               n_procs=n_procs)

        elevation -= deflection

    def subside_loads(self, loads, locs, deflection=None, n_procs=1):
        if deflection is None:
            deflection = np.empty(self.shape, dtype=np.float)

        subside_point_loads(loads, locs, self.coords, self._eet, self._youngs,
                            deflection=deflection, n_procs=n_procs)

        return deflection

    def subside_load(self, load, loc, deflection=None):
        subside_point_load(
            load, loc, self.coords, self._eet, self._youngs,
            deflection=self.grid['lithosphere__elevation_increment'])

        return deflection


if __name__ == "__main__":
    import doctest
    doctest.testmod()
