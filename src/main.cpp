#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "simulation.h"

namespace py = pybind11;

PYBIND11_MODULE(sim_core, m) {
    py::class_<SimEvent>(m, "SimEvent")
        .def_readonly("timestamp", &SimEvent::timestamp)
        .def_readonly("phil_id", &SimEvent::phil_id)
        .def_readonly("event_type", &SimEvent::event_type)
        .def_readonly("details", &SimEvent::details);

    py::class_<Simulation>(m, "Simulation")
        .def(py::init<int,int>())
        .def("start", &Simulation::start)
        .def("stop", &Simulation::stop)
        .def("set_strategy", &Simulation::set_strategy)
        .def("get_states", &Simulation::get_states)
        .def("get_resource_graph", &Simulation::get_resource_graph)
        .def("poll_events", &Simulation::poll_events)
        .def("detect_deadlock", &Simulation::detect_deadlock);
}