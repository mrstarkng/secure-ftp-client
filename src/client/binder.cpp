#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>
#include "../core/command_handler.h"
#include "../common/socket_utils.h"

namespace py = pybind11;

PYBIND11_MODULE(ftp_engine, m) {
    m.doc() = "Secure FTP Client C++ Backend";
    py::register_exception<FtpException>(m, "FtpException");

    py::class_<CommandHandler>(m, "FtpClient")
        .def(py::init<>())

        // --- 3. Session Management ---
        .def("open", &CommandHandler::handle_open, py::arg("args"), py::call_guard<py::gil_scoped_release>())
        .def("close", &CommandHandler::handle_close, py::call_guard<py::gil_scoped_release>())
        .def("quit", &CommandHandler::handle_quit, py::call_guard<py::gil_scoped_release>())
        .def("bye", &CommandHandler::handle_quit, py::call_guard<py::gil_scoped_release>()) // Alias
        .def("status", &CommandHandler::handle_status, py::call_guard<py::gil_scoped_release>())
        .def("passive", &CommandHandler::handle_passive, py::arg("args"), py::call_guard<py::gil_scoped_release>())
        .def("binary", &CommandHandler::handle_binary, py::call_guard<py::gil_scoped_release>())
        .def("ascii", &CommandHandler::handle_ascii, py::call_guard<py::gil_scoped_release>())
        .def("prompt", &CommandHandler::handle_prompt, py::call_guard<py::gil_scoped_release>())
        .def("help", &CommandHandler::handle_help, py::call_guard<py::gil_scoped_release>())
        .def("?", &CommandHandler::handle_help, py::call_guard<py::gil_scoped_release>()) // Alias

        // --- 1. File and Directory Operations ---
        .def("ls", &CommandHandler::handle_ls, py::arg("args"), py::call_guard<py::gil_scoped_release>())
        .def("cd", &CommandHandler::handle_cd, py::arg("args"), py::call_guard<py::gil_scoped_release>())
        .def("pwd", &CommandHandler::handle_pwd, py::call_guard<py::gil_scoped_release>())
        .def("mkdir", &CommandHandler::handle_mkdir, py::arg("args"), py::call_guard<py::gil_scoped_release>())
        .def("rmdir", &CommandHandler::handle_rmdir, py::arg("args"), py::call_guard<py::gil_scoped_release>())
        .def("delete", &CommandHandler::handle_delete, py::arg("args"), py::call_guard<py::gil_scoped_release>())
        .def("rename", &CommandHandler::handle_rename, py::arg("args"), py::call_guard<py::gil_scoped_release>())

        // --- 2. Upload and Download ---
        .def("get", &CommandHandler::handle_get, py::arg("args"), py::call_guard<py::gil_scoped_release>())
        .def("recv", &CommandHandler::handle_get, py::arg("args"), py::call_guard<py::gil_scoped_release>()) // Alias
        .def("put", &CommandHandler::handle_put, py::arg("args"), py::call_guard<py::gil_scoped_release>())
        .def("mget", &CommandHandler::handle_mget, py::arg("args"), py::call_guard<py::gil_scoped_release>())
        .def("mput", &CommandHandler::handle_mput, py::arg("args"), py::call_guard<py::gil_scoped_release>())
        
        // --- Direct File Operations for Python ---
        .def("uploadFile", &CommandHandler::uploadFile, py::arg("local"), py::arg("remote"), py::call_guard<py::gil_scoped_release>())
        .def("downloadFile", &CommandHandler::downloadFile, py::arg("remote"), py::arg("local"), py::call_guard<py::gil_scoped_release>())
        .def("uploadFileWithProgress", &CommandHandler::uploadFileWithProgress, py::arg("local"), py::arg("remote"), py::arg("callback"), py::call_guard<py::gil_scoped_release>())
        .def("downloadFileWithProgress", &CommandHandler::downloadFileWithProgress, py::arg("remote"), py::arg("local"), py::arg("callback"), py::call_guard<py::gil_scoped_release>())
        
        // --- Connection Management for Python ---
        .def("connect", &CommandHandler::connect, py::arg("host"), py::arg("port"), py::call_guard<py::gil_scoped_release>())
        .def("login", &CommandHandler::login, py::arg("username"), py::arg("password"), py::call_guard<py::gil_scoped_release>())
        .def("setPassive", &CommandHandler::setPassive, py::arg("passive"), py::call_guard<py::gil_scoped_release>())
        .def("disconnect", &CommandHandler::disconnect, py::call_guard<py::gil_scoped_release>())
        .def("isConnected", &CommandHandler::isConnected, py::call_guard<py::gil_scoped_release>());
}