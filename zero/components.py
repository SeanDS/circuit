"""Electronic components"""

import abc
from collections.abc import MutableMapping
import numpy as np

from .misc import NamedInstance
from .format import Quantity
from .config import ZeroConfig, LibraryOpAmp

CONF = ZeroConfig()


class Component(metaclass=abc.ABCMeta):
    """Represents a circuit component.

    Parameters
    ----------
    name : :class:`str`, optional
        The component name. Must be unique.
    nodes : sequence of :class:`~Node` or :class:`str`, optional
        The component nodes.

    Attributes
    ----------
    noise : :class:`set` of :class:`.ComponentNoise`
        The component noise sources.
    """

    TYPE = "component"
    BASE_NAME = "?"
    UNIT = "A"

    def __init__(self, name=None, nodes=None):
        if name is not None:
            name = str(name)

        if nodes is None:
            nodes = []

        # defaults
        self._nodes = []
        self.noise = []

        # whether name was autogenerated
        self.autonamed = False

        self.name = name
        self.nodes = nodes

    @property
    def nodes(self):
        """The component nodes.

        Returns
        -------
        :class:`list` of :class:`~Node`
            The component nodes.
        """
        return self._nodes

    @nodes.setter
    def nodes(self, nodes):
        for node in list(nodes):
            if not isinstance(node, Node):
                # parse node name
                node = Node(str(node))

            self._nodes.append(node)

    def add_noise(self, noise):
        """Add a noise source to the component.

        Parameters
        ----------
        noise : :class:`~Noise`
            The noise to add.

        Raises
        ------
        ValueError
            If specified noise is already present.
        """
        if noise in self.noise:
            raise ValueError("specified noise '%s' already exists in '%s'" % (noise, self))

        self.noise.append(noise)

    def label(self):
        """Get component label.

        Returns
        -------
        :class:`str`
            The component label.
        """
        name = self.name

        if name is None:
            # name not set
            name = "%s (no name)" % self.__class__.__name__

        return name

    def __repr__(self):
        return str(self)

    def __str__(self):
        return self.label()

    def __eq__(self, other):
        return self.name == getattr(other, "name", None)

    def __hash__(self):
        """Components uniquely defined by their name"""
        return hash((self.name))


class PassiveComponent(Component, metaclass=abc.ABCMeta):
    """Represents a passive component.

    A passive component is one that consumes or temporarily stores energy, but
    does not produce or amplify it. Examples include
    :class:`resistors <Resistor>`, :class:`capacitors <Capacitor>` and
    :class:`inductors <Inductor>`.

    Parameters
    ----------
    value : any, optional
        The component value.
    node1 : :class:`~Node`, optional
        The first component node.
    node2 : :class:`~Node`, optional
        The second component node.

    Attributes
    ----------
    value : :class:`float`
        The component value.
    """

    UNIT = "?"

    def __init__(self, value=None, node1=None, node2=None, *args, **kwargs):
        super().__init__(nodes=[node1, node2], *args, **kwargs)
        self.value = value

    @property
    def value(self):
        """The component value.

        Returns
        -------
        :class:`float`
            The component value.
        """
        return self._value

    @value.setter
    def value(self, value):
        if value is not None:
            value = Quantity(value, self.UNIT)

        self._value = value

    @property
    def node1(self):
        """The first component node.

        Returns
        -------
        :class:`.Node`
            The first component node.
        """
        return self.nodes[0]

    @node1.setter
    def node1(self, node):
        self.nodes[0] = node

    @property
    def node2(self):
        """The second component node.

        Returns
        -------
        :class:`.Node`
            The second component node.
        """
        return self.nodes[1]

    @node2.setter
    def node2(self, node):
        self.nodes[1] = node

    @abc.abstractmethod
    def impedance(self, frequency):
        """The passive impedance."""
        return NotImplemented


class OpAmp(LibraryOpAmp, Component):
    """Represents an (almost) ideal op-amp.

    An op-amp produces :class:`voltage noise <VoltageNoise>` across its input
    and output :class:`nodes <Node>`, and :class:`current noise <CurrentNoise>`
    is present at its input :class:`nodes <Node>`.

    Parameters
    ----------
    node1 : :class:`Node`
        Non-inverting input node.
    node2 : :class:`Node`
        Inverting input node.
    node3 : :class:`Node`
        Output node.
    """
    TYPE = "op-amp"
    BASE_NAME = "op"

    def __init__(self, node1, node2, node3, **kwargs):
        # call parent constructor
        super().__init__(nodes=[node1, node2, node3], **kwargs)

        # op-amp voltage noise
        self.add_noise(VoltageNoise(component=self,
                                    function=self._noise_voltage))

        # op-amp input current noise
        if self.node1 is not Node("gnd"):
            # non-inverting input noise
            self.add_noise(CurrentNoise(node=self.node1, component=self,
                                        function=self._noise_current))
        if self.node2 is not Node("gnd"):
            # inverting input noise
            self.add_noise(CurrentNoise(node=self.node2, component=self,
                                        function=self._noise_current))

    @property
    def node1(self):
        return self.nodes[0]

    @node1.setter
    def node1(self, node):
        self.nodes[0] = node

    @property
    def node2(self):
        return self.nodes[1]

    @node2.setter
    def node2(self, node):
        self.nodes[1] = node

    @property
    def node3(self):
        return self.nodes[2]

    @node3.setter
    def node3(self, node):
        self.nodes[2] = node

    def _noise_voltage(self, component, frequencies):
        return self.params["vnoise"] * np.sqrt(1 + self.params["vcorner"] / frequencies)

    def _noise_current(self, node, frequencies):
        # ignore node; noise is same at both inputs
        return self.params["inoise"] * np.sqrt(1 + self.params["icorner"] / frequencies)

    @property
    def voltage_noise(self):
        for noise in self.noise:
            if noise.SUBTYPE == "voltage":
                return noise

        raise NoiseNotFoundError("voltage noise")

    @property
    def non_inv_current_noise(self):
        for noise in self.noise:
            if noise.SUBTYPE == "current":
                if noise.node == self.node1:
                    return noise

        raise NoiseNotFoundError("non-inverting current noise")

    @property
    def inv_current_noise(self):
        for noise in self.noise:
            if noise.SUBTYPE == "current":
                if noise.node == self.node2:
                    return noise

        raise NoiseNotFoundError("inverting current noise")

    def __str__(self):
        return super().__str__() + " [in+={cmp.node1}, in-={cmp.node2}, out={cmp.node3}, model={cmp.model}]".format(cmp=self)


class Input(Component):
    """Represents the circuit's voltage input"""

    TYPE = "input"
    BASE_NAME = "in"

    def __init__(self, input_type, node=None, node_p=None, node_n=None,
                 impedance=None, *args, **kwargs):
        # default input nodes
        nodes = None

        # handle nodes
        if node is not None:
            if node_p is not None or node_n is not None:
                raise ValueError("node cannot be specified alongside node_p or node_n")

            nodes = [Node("gnd"), node]
        else:
            if node_p is None and node_n is None:
                # no nodes specified
                raise ValueError("input node(s) must be specified")
            elif node_p is None or node_n is None:
                # only one of node_p or node_n specified
                raise ValueError("node_p and node_n must both be specified")

            nodes = [node_n, node_p]

        input_type = input_type.lower()

        if input_type == "noise":
            self.input_type = "noise"

            if impedance is None:
                raise ValueError("impedance must be specified for noise input")

            impedance = Quantity(impedance, "Ω")
        else:
            if impedance is not None:
                raise ValueError("impedance cannot be specified for non-noise input")

            if input_type == "voltage":
                self.input_type = "voltage"
            elif input_type == "current":
                self.input_type = "current"
                # assume 1 ohm impedance for transfer functions
                impedance = 1
            else:
                raise ValueError("unrecognised input type")

        self.impedance = impedance

        # call parent constructor
        super().__init__(name="input", nodes=nodes, *args, **kwargs)

    @property
    def node1(self):
        return self.nodes[0]

    @node1.setter
    def node1(self, node):
        self.nodes[0] = node

    @property
    def node2(self):
        return self.nodes[1]

    @node2.setter
    def node2(self, node):
        self.nodes[1] = node

    @property
    def node_n(self):
        return self.node1

    @node_n.setter
    def node_n(self, node):
        self.node1 = node

    @property
    def node_p(self):
        return self.node2

    @node_p.setter
    def node_p(self, node):
        self.node2 = node

    def __str__(self):
        if self.impedance:
            z = self.impedance
        else:
            z = "default"

        return super().__str__() + " [in={cmp.node1}, out={cmp.node2}, Z={z}]".format(cmp=self, z=z)


class Resistor(PassiveComponent):
    """Represents a resistor or set of series or parallel resistors"""

    UNIT = "Ω"
    TYPE = "resistor"
    BASE_NAME = "r"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # register Johnson noise
        self.add_noise(JohnsonNoise(component=self, resistance=self.resistance))

    @property
    def resistance(self):
        """Resistance in ohms."""
        return self.value

    @resistance.setter
    def resistance(self, resistance):
        self.value = resistance

    def impedance(self, *args):
        """The impedance.

        Returns
        -------
        :class:`complex`
            The impedance.
        """
        return self.resistance

    @property
    def johnson_noise(self):
        for noise in self.noise:
            if noise.SUBTYPE == "johnson":
                return noise

        raise ValueError("no Johnson noise")

    def __str__(self):
        return super().__str__() + " [in={cmp.node1}, out={cmp.node2}, R={cmp.resistance}]".format(cmp=self)


class Capacitor(PassiveComponent):
    """Represents a capacitor or set of series or parallel capacitors"""

    UNIT = "F"
    TYPE = "capacitor"
    BASE_NAME = "c"

    @property
    def capacitance(self):
        """Capacitance in farads."""
        return self.value

    @capacitance.setter
    def capacitance(self, capacitance):
        self.value = capacitance

    def impedance(self, frequency):
        """The impedance.

        Parameters
        ----------
        frequency : :class:`float` or array_like

        Returns
        -------
        :class:`complex`
            The impedance.
        """
        return 1 / (2j * np.pi * frequency * self.capacitance)

    def __str__(self):
        return super().__str__() + " [in={cmp.node1}, out={cmp.node2}, C={cmp.capacitance}]".format(cmp=self)


class Inductor(PassiveComponent):
    """Represents an inductor or set of series or parallel inductors"""

    UNIT = "H"
    TYPE = "inductor"
    BASE_NAME = "l"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # default inductor coupling factor map
        self.coupling_factors = CouplingFactorDict(self)

    @property
    def inductance(self):
        """Inductance in henries."""
        return self.value

    @inductance.setter
    def inductance(self, inductance):
        self.value = inductance

    def impedance(self, frequency):
        """The impedance.

        Parameters
        ----------
        frequency : :class:`float` or array_like
            The frequency.

        Returns
        -------
        :class:`complex`
            The impedance.
        """
        return 2j * np.pi * frequency * self.inductance

    def inductance_from(self, other):
        """Calculate the mutual inductance this inductor has with the specified inductor

        Parameters
        ----------
        other : :class:`Inductor`
            The other inductor.

        Returns
        -------
        :class:`.Quantity`
            The mutual inductance between this inductor and the specified one.

        Raises
        ------
        :class:`TypeError`
            If the specified inductor is not of type :class:`Inductor`
        """
        if not isinstance(other, self.__class__):
            raise TypeError("specified component '%s' is not an inductor" % other)

        coupling_factor = self.coupling_factors[other]
        mutual_inductance = coupling_factor * np.sqrt(self.inductance * other.inductance)

        return Quantity(mutual_inductance, unit=self.UNIT)

    def impedance_from(self, other, frequency):
        """Calculate the impedance this inductor has due to the specified coupled inductor

        Parameters
        ----------
        other : :class:`Inductor`
            The other inductor.
        frequency : :class:`float` or array_like
            The frequency.

        Returns
        -------
        :class:`complex`
            The impedance.
        """
        return 2j * np.pi * frequency * self.inductance_from(other)

    @property
    def coupled_inductors(self):
        """Inductors coupled to this one"""
        return self.coupling_factors.keys()

    def __str__(self):
        return super().__str__() + " [in={cmp.node1}, out={cmp.node2}, L={cmp.inductance}]".format(cmp=self)


class Node(metaclass=NamedInstance):
    """Represents a circuit node (connection between components)

    Nodes are considered equal if they have the same case-independent name.

    Parameters
    ----------
    name : :class:`str`
        Node name.

    Attributes
    ----------
    sources : :class:`set`
        :class:`Components <Component>` that source current connected to this
        node.
    sinks : :class:`set`
        :class:`Components <Component>` that sink current connected to this
        node.
    """

    UNIT = "V"

    def __init__(self, name):
        """Instantiate a new node."""

        self.name = str(name)

    def label(self):
        return self.name

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)


class Noise(metaclass=abc.ABCMeta):
    """Noise spectral density.

    Parameters
    ----------
    function : callable
        Callable that returns the noise associated with a specified frequency
        vector.
    """

    TYPE = ""

    def __init__(self, function=None):
        self.function = function

    @abc.abstractmethod
    def spectral_density(self, frequencies):
        return NotImplemented

    @abc.abstractmethod
    def label(self):
        return NotImplemented

    def _meta_data(self):
        """Meta data used to provide hash."""
        return tuple(self.label())

    def __str__(self):
        return self.label()

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return hash(self._meta_data())


class ComponentNoise(Noise, metaclass=abc.ABCMeta):
    """Component noise spectral density.

    Parameters
    ----------
    component : :class:`Component`
        Component associated with the noise.
    """

    TYPE = "component"

    def __init__(self, component, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.component = component

    def spectral_density(self, frequencies):
        return self.function(component=self.component, frequencies=frequencies)

    def _meta_data(self):
        """Meta data used to provide hash."""
        return super()._meta_data(), self.component


class NodeNoise(Noise, metaclass=abc.ABCMeta):
    """Node noise spectral density.

    Parameters
    ----------
    node : :class:`Node`
        Node associated with the noise.
    component : :class:`Component`
        Component associated with the noise.
    """

    TYPE = "node"

    def __init__(self, node, component, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.node = node
        self.component = component

    def spectral_density(self, *args, **kwargs):
        return self.function(node=self.node, *args, **kwargs)

    def _meta_data(self):
        """Meta data used to provide hash."""
        return super()._meta_data(), self.node, self.component


class VoltageNoise(ComponentNoise):
    SUBTYPE = "voltage"

    def label(self):
        return "V(%s)" % self.component.name


class JohnsonNoise(VoltageNoise):
    SUBTYPE = "johnson"

    def __init__(self, resistance, *args, **kwargs):
        super().__init__(function=self.noise_voltage, *args, **kwargs)

        self.resistance = float(resistance)

    def noise_voltage(self, frequencies, *args, **kwargs):
        white_noise = np.sqrt(4 * float(CONF["constants"]["kB"])
                                * float(CONF["constants"]["T"])
                                * self.resistance)

        return np.ones(frequencies.shape) * white_noise

    def label(self):
        return "R(%s)" % self.component.name

    def _meta_data(self):
        """Meta data used to provide hash."""
        return super()._meta_data(), self.resistance


class CurrentNoise(NodeNoise):
    SUBTYPE = "current"

    def label(self):
        return "I(%s, %s)" % (self.component.name, self.node.name)


class NoiseNotFoundError(ValueError):
    def __init__(self, noise_description, *args, **kwargs):
        message = "%s not found" % noise_description
        super().__init__(message, *args, **kwargs)


class CouplingFactorDict(MutableMapping):
    """Collection to get and set coupling factors between inductors"""
    def __init__(self, inductor, *args, **kwargs):
        self.inductor = inductor

        # create dict to store things
        self._couplings = dict()

        # initialise data
        self.update(dict(*args, **kwargs))

    def __getitem__(self, inductor):
        """Get coupling factor for specified inductor

        If there is no coupling factor defined between the inductors, it is assumed to be zero.

        Parameters
        ----------
        inductor : :class:`.Inductor`
            The inductor to get the coupling for.

        Returns
        -------
        :class:`.Quantity`
            The coupling factor.

        Raises
        ------
        :class:`TypeError`
            If the specified component is not an inductor.
        """
        if not isinstance(inductor, Inductor):
            raise TypeError("specified component, '%s', is not an inductor" % inductor)

        return self._couplings.get(inductor, 0)

    def __setitem__(self, inductor, coupling_factor):
        """Set coupling factor for specified inductor

        Parameters
        ----------
        inductor : :class:`.Inductor`
            The inductor to couple to the inductor contained within this.
        coupling_factor : any
            The coupling factor to use.

        Raises
        ------
        :class:`TypeError`
            If the specified component is not an inductor.
        :class:`ValueError`
            If the specified coupling factor is outside the range [0, 1].
        """
        if not isinstance(inductor, Inductor):
            raise TypeError("specified component, '%s', is not an inductor" % inductor)

        # parse value
        coupling_factor = Quantity(coupling_factor)

        if coupling_factor < 0 or coupling_factor > 1:
            raise ValueError("specified coupling factor must be between 0 and 1")

        self._couplings[inductor] = coupling_factor

    def __delitem__(self, key):
        del self._couplings[key]

    def __iter__(self):
        return iter(self._couplings)

    def __len__(self):
        return len(self._couplings)

    def __contains__(self, key):
        return key in self._couplings
