"""Electronic circuit class to which linear components can be added and
on which simulations can be performed."""

import sys
import numpy as np
import logging

from .config import CircuitConfig, OpAmpLibrary
from .components import (Component, Resistor, Capacitor, Inductor, OpAmp,
                         Input, Node)
from .display import NodeGraph

LOGGER = logging.getLogger("circuit")
CONF = CircuitConfig()
LIBRARY = OpAmpLibrary()

class Circuit(object):
    """Represents an electronic circuit containing components.

    A circuit can contain components like :class:`resistors <.components.Resistor>`,
    :class:`capacitors <.components.Capacitor>`, :class:`inductors <.components.Inductor>`
    and :class:`op-amps <.components.OpAmp>`. These are added to the circuit via the
    :meth:`add_component` method.

    Attributes
    ----------
    components : :class:`list` of :class:`.Component`
        The circuit components.
    """

    def __init__(self):
        # empty lists of components and nodes
        self.components = []

    @property
    def nodes(self):
        """Circuit nodes, including ground if present.
        
        Returns
        -------
        :class:`set` of :class:`.Node`
            The circuit nodes.
        """
        return set([node for component in self.components for node in component.nodes])

    @property
    def non_gnd_nodes(self):
        """Circuit nodes, excluding ground.

        Returns
        -------
        :class:`list` of :class:`.Node`
            The circuit nodes.
        """
        return [node for node in self.nodes if node is not Node("gnd")]

    @property
    def elements(self):
        """Circuit nodes and components.
        
        Yields
        ------
        :class:`.Node`
            The circuit nodes.
        :class:`.Component`
            The circuit components.
        """
        yield from self.non_gnd_nodes
        yield from self.components

    @property
    def opamp_output_nodes(self):
        """Circuit op-amp output nodes.

        Returns
        -------
        :class:`list` of :class:`.Node`
            The op-amp output nodes.
        """
        return [opamp.node3 for opamp in self.opamps]

    def add_component(self, component):
        """Add existing component to circuit.

        Parameters
        ----------
        component : :class:`.Component`
            The component to add.

        Raises
        ------
        ValueError
            If component is None, or already present in the circuit.
        """

        if component is None:
            raise ValueError("component cannot be None")
        elif component in self.components:
            raise ValueError("component %s already in circuit" % component)

        # add component to end of list
        self.components.append(component)

    def add_input(self, *args, **kwargs):
        """Add input to circuit."""
        self.add_component(Input(*args, **kwargs))

    def add_resistor(self, *args, **kwargs):
        """Add resistor to circuit."""
        self.add_component(Resistor(*args, **kwargs))

    def add_capacitor(self, *args, **kwargs):
        """Add capacitor to circuit."""
        self.add_component(Capacitor(*args, **kwargs))

    def add_inductor(self, *args, **kwargs):
        """Add inductor to circuit."""
        self.add_component(Inductor(*args, **kwargs))

    def add_opamp(self, *args, **kwargs):
        """Add op-amp to circuit."""
        self.add_component(OpAmp(*args, **kwargs))

    def add_library_opamp(self, model, **kwargs):
        """Add library op-amp to circuit.
        
        Keyword arguments can be used to override individual library parameters.

        Parameters
        ----------
        model : :class:`str`
            The op-amp model name.
        """
        # get library data
        data = LIBRARY.get_data(model)

        # override library data with keyword arguments
        data = {**data, **kwargs}

        self.add_opamp(model=OpAmpLibrary.format_name(model), **data)

    def remove_component(self, component):
        """Remove component from circuit.

        Parameters
        ----------
        component : :class:`str` or :class:`.Component`
            The component to remove.
        
        Raises
        ------
        ValueError
            If the component is not in the circuit.
        """
        # remove
        self.components.remove(component)

    def get_component(self, component_name):
        """Get circuit component by name.

        Parameters
        ----------
        component_name : str
            The name of the component to fetch.

        Returns
        -------
        :class:`.Component`
            The component.

        Raises
        ------
        ValueError
            If the component is not found.
        """
        component_name = component_name.lower()

        for component in self.components:
            if component.name.lower() == component_name:
                return component

        raise ValueError("component %s not found" % component_name)

    def get_node(self, node_name):
        """Get circuit node by name.

        Parameters
        ----------
        node_name : :class:`str`
            The name of the node to fetch.

        Returns
        -------
        :class:`.Node`
            The node.

        Raises
        ------
        ValueError
            If the node is not found.
        """
        node_name = node_name.lower()

        for node in self.nodes:
            if node.name.lower() == node_name:
                return node

        raise ValueError("node %s not found" % node_name)

    def get_noise(self, noise_name):
        """Get noise by component or node name.

        Parameters
        ----------
        noise_name : :class:`str`
            The name of the noise to fetch.
        
        Returns
        -------
        :class:`Noise`
            The noise.
        
        Raises
        ------
        ValueError
            If the noise is not found.
        """
        noise_name = noise_name.lower()

        for noise in self.noise_sources:
            if noise_name == noise.label().lower():
                return noise
        
        raise ValueError("noise not found")

    @property
    def n_components(self):
        """The number of components in the circuit.

        Returns
        -------
        :class:`int`
            The number of components.
        """
        return len(self.components)

    @property
    def n_nodes(self):
        """The number of nodes in the circuit.

        Returns
        -------
        :class:`int`
            The number of nodes.
        """
        return len(self.nodes)

    @property
    def resistors(self):
        """The circuit resistors.

        Returns
        -------
        :class:`list` of :class:`.Resistor`
            The resistors in the circuit.
        """
        return [component for component in self.components if component.TYPE == "resistor"]

    @property
    def capacitors(self):
        """The circuit capacitors.

        Returns
        -------
        :class:`list` of :class:`.Capacitor`
            The capacitors in the circuit.
        """
        return [component for component in self.components if component.TYPE == "capacitor"]

    @property
    def inductors(self):
        """The circuit inductors.

        Returns
        -------
        :class:`list` of :class:`.Inductor`
            The inductors in the circuit.
        """
        return [component for component in self.components if component.TYPE == "inductor"]

    @property
    def passive_components(self):
        """The circuit passive components.
        
        Yields
        ------
        :class:`.Resistor`
            The resistors in the circuit.
        :class:`.Capacitor`
            The capacitors in the circuit.
        :class:`.Inductor`
            The inductors in the circuit.
        """
        yield from self.resistors
        yield from self.capacitors
        yield from self.inductors

    @property
    def opamps(self):
        """The op-amps in the circuit.

        Returns
        -------
        :class:`list` of :class:`.OpAmp`
            The op-amps.
        """
        return [component for component in self.components if component.TYPE == "op-amp"]

    @property
    def noise_sources(self):
        """The noise sources in the circuit.

        Returns
        -------
        :class:`list` of :class:`.ComponentNoise` or :class:`.NodeNoise`
            The component and node noise sources.
        """
        return [noise for component in self.components for noise in component.noise]

    @property
    def input_component(self):
        """The circuit input component.
        
        Returns
        -------
        :class:`.Input`
            The circuit input.
        """
        return self.get_component("input")

    @property
    def input_impedance(self):
        """The circuit input impedance.
        
        Returns
        -------
        :class:`float`
            circuit input impedance
        """
        return self.input_component.impedance

    @property
    def has_input(self):
        """Whether the circuit has an input.
        
        Returns
        -------
        :class:`bool`
            True if the circuit has an input, False otherwise.
        """
        try:
            self.input_component
        except ValueError:
            return False

        return True
    
    def __repr__(self):
        """Circuit text representation"""
        if self.n_components > 1:
            cmp_str = "components"
        else:
            cmp_str = "component"

        if self.n_nodes > 1:
            node_str = "nodes"
        else:
            node_str = "node"

        text = "Circuit with {n_cmps} {cmp_str} and {n_nodes} {node_str}".format(
            n_cmps=self.n_components, cmp_str=cmp_str, n_nodes=self.n_nodes, node_str=node_str)
        
        if self.n_components > 0:
            text += "\n"

            # field size
            iw = int(np.ceil(np.log10(len(self.components))))

            for index, component in enumerate(sorted(self.components, key=lambda cmp: (cmp.__class__.__name__, cmp.name)), start=1):
                text += "\n\t{index:{iw}}. {cmp}".format(index=index, iw=iw, cmp=component)

        return text