#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "simulation.h"

namespace py = pybind11;

PYBIND11_MODULE(sim_core, m) {
    py::class_<Simulation>(m, "Simulation")
        .def(py::init<int,int>())
        .def("start", &Simulation::start)
        .def("stop", &Simulation::stop)
        .def("get_states", &Simulation::get_states)
        .def("get_resource_graph", &Simulation::get_resource_graph);
}