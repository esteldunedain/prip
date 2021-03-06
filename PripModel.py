# Prip
# class PripModel

from PyQt4 import QtCore, QtGui
from PripInsertMode import PripInsertMode
from collections import OrderedDict
from vector import vector_diff, solve_linear_2x2
import pickle
from os import path

class PripModel(QtCore.QObject):

    # Signals
    model_changed = QtCore.pyqtSignal()

    @property
    def x0(self):
        return self._x0
    @x0.setter
    def x0(self, value):
        self._x0 = value

    @property
    def x1(self):
        return self._x1
    @x1.setter
    def x1(self, value):
        self._x1 = value

    @property
    def y0(self):
        return self._y0
    @y0.setter
    def y0(self, value):
        self._y0 = value

    @property
    def y1(self):
        return self._y1
    @y1.setter
    def y1(self, value):
        self._y1 = value

    def __init__(self):
        QtCore.QObject.__init__(self, None)
        self.reset()

    def reset(self):
        self._point_index = 0
        self._background_file = None

        self._axis_refs = {}
        self._axis_lines = {}

        self._points = OrderedDict()

        self._datasets = OrderedDict()
        self._dataset_key = 0
        self._current_dataset = None

        self._mode = PripInsertMode.Normal

        self.x0 = 0.0
        self.x1 = 1.0
        self.y0 = 0.0
        self.y1 = 1.0

    def new_project(self, background_file = None):
        self.reset()
        if not background_file is None:
            self.add_image(background_file)
        self.add_dataset()

    def save_project(self, project_file):
        # Construct dict to dump
        d = {}
        dir_name = path.dirname(str(project_file))
        rel_path = path.relpath(str(self._background_file), str(dir_name))
        d["background_file"] = str(rel_path)
        d["x0"] = self.x0
        d["x1"] = self.x1
        d["y0"] = self.y0
        d["y1"] = self.y1

        # Store axis refs coordinates
        axis_refs = {}
        for key in self._axis_refs:
            if self._axis_refs[key] is None:
                axis_refs[key] = None
            else:
                axis_refs[key] = self._axis_refs[key]
        d["axis_refs"] = axis_refs

        # Store items coordinates
        points = []
        for key in self._points:
            p, dataset = self._points[key]
            points.append([p, dataset])
        d["points"] = points

        datasets = self._datasets
        dataset_key = self._dataset_key
        current_dataset = self._current_dataset
        d["datasets"] = datasets
        d["dataset_key"] = dataset_key
        d["current_dataset"] = current_dataset

        try:
            oF = open(project_file, "wb")
            pickle.dump("PripV0.3", oF)
            pickle.dump(d, oF)
            oF.close()
            return True
        except:
            return False

    def load_project(self, project_file):
        self.reset()

        with open(project_file, "rb") as iF:
            header = pickle.load(iF)
            if header == "PripV0.1" or header == "PripV0.2" or header == "PripV0.3":
                d = pickle.load(iF)

                def assignIfExists(var, d, keyname):
                    if keyname in d:
                        return d[keyname]
                    else:
                        return var

                background_file = d["background_file"]
                if header == "PripV0.3":
                    dir_name = path.dirname(str(project_file))
                    background_file = path.normpath(path.join(dir_name, background_file))
                print background_file

                self.add_image(background_file)
                self.x0 = assignIfExists(self.x0, d, "x0")
                self.x1 = assignIfExists(self.x1, d, "x1")
                self.y0 = assignIfExists(self.y0, d, "y0")
                self.y1 = assignIfExists(self.y1, d, "y1")

                for key in d["axis_refs"]:
                    if not d["axis_refs"][key] is None:
                        p = d["axis_refs"][key]
                        if isinstance(p, QtCore.QPointF):
                            p = [p.x(), p.y()]
                        self.add_axis_ref(p, key)

                if "datasets" in d:
                    self._datasets = d["datasets"]
                    self._dataset_key = d["dataset_key"]
                    self._current_dataset = d["current_dataset"]
                else:
                    self._datasets = OrderedDict({0: "Dataset 0"})
                    self._dataset_key = 1
                    self._current_dataset = 0

                for data in d["points"]:
                    p, dataset = [0,0], 0
                    if isinstance(data, list) or isinstance(data, tuple):
                        p, dataset = data
                    elif isinstance(data, QtCore.QPointF):
                        p = [data.x(), data.y()]
                    else:
                        continue
                    if dataset in self._datasets:
                        self._current_dataset = dataset
                    self.add_point(p)

                self.model_changed.emit()
                return True

        self.model_changed.emit()
        return False

    def add_image(self, background_file):
        self._background_file = str(background_file)

    def get_background_file(self):
        return self._background_file

    def get_insert_mode(self):
        return self._mode

    def set_insert_mode(self, mode):
        self._mode = mode

    def get_points(self):
        return self._points

    def add_point(self, pos):
        self._points[self._point_index] = [pos, self._current_dataset]
        self._point_index += 1

        self.model_changed.emit()

    def remove_point(self, key):
        del self._points[key]
        self.model_changed.emit()

    def move_point(self, key, pos):
        if not key in self._points:
            return
        self._points[key][0] = pos
        self.model_changed.emit()

    def get_axis_refs(self):
        return self._axis_refs

    def add_axis_ref(self, pos, key):
        self._axis_refs[key] = pos
        self.model_changed.emit()

    def move_axis_ref(self, key, pos):
        if not key in self._axis_refs:
            return
        self._axis_refs[key] = pos
        self.model_changed.emit()

    def compute_coordinates(self, pos):
        if len(self._axis_refs.keys()) != 4:
            return pos

        coord = [0,0]
        x0Pos = self._axis_refs[PripInsertMode.X0]
        x1Pos = self._axis_refs[PripInsertMode.X1]
        y0Pos = self._axis_refs[PripInsertMode.Y0]
        y1Pos = self._axis_refs[PripInsertMode.Y1]

        # Find projecting over x axis
        A = [vector_diff(x1Pos, x0Pos),
             vector_diff(y1Pos, y0Pos)]

        b = vector_diff(pos, x0Pos)

        [alpha, beta] = solve_linear_2x2(A, b)
        coord[0] = self.x0 + (self.x1 - self.x0) * alpha

        # Find projecting over y axis
        b = vector_diff(pos, y0Pos)

        [alpha, beta] = solve_linear_2x2(A, b)
        coord[1] = self.y0 + (self.y1 - self.y0) * beta

        return coord

    def get_points_per_dataset(self):
        points_per_dataset = OrderedDict()
        for dataset in self._datasets:
            points_per_dataset[dataset] = []

        for key in self._points:
            p, dataset = self._points[key]
            points_per_dataset[dataset].append(p)

        count = max(len(points_per_dataset[dataset]) for dataset in self._datasets)
        return points_per_dataset, count

    def export_data_clipboard(self):
        points_per_dataset, count = self.get_points_per_dataset()

        clipboard_text = ""
        for i in range(count):
            for dataset in self._datasets:
                if i < len(points_per_dataset[dataset]):
                    p = points_per_dataset[dataset][i]
                    clipboard_text += ("%f\t%f\t" % tuple(self.compute_coordinates(p)))
                else:
                    clipboard_text += "\t\t"
            clipboard_text += "\n"

        cb = QtGui.QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText(clipboard_text)

    def export_data_textfile(self, filename = None):
        points_per_dataset, count = self.get_points_per_dataset()

        if filename is None:
            filename = self._background_file + ".dat"

        with open(filename, "w") as oF:
            for i in range(count):
                for dataset in self._datasets:
                    if i < len(points_per_dataset[dataset]):
                        p = points_per_dataset[dataset][i]
                        oF.write("%f, %f, " % tuple(self.compute_coordinates(p)))
                    else:
                        oF.write(", , ")
                oF.write("\n")

    def add_dataset(self, name = None):
        if name is None:
            name = "Dataset %i" % self._dataset_key

        key = self._dataset_key
        self._datasets[key] = name
        self._current_dataset = key
        self._dataset_key += 1
        self.model_changed.emit()

    def remove_dataset(self, key):
        del self._datasets[key]

        # Delete dangling points
        for pkey in self._points.keys():
            if self._points[pkey][1] == key:
                del self._points[pkey]

        if self._current_dataset == key:
            if len(self._datasets.keys()) == 0:
                # If the last dataset was removed, add a new one instead
                self.add_dataset()
            self._current_dataset = self._datasets.keys()[-1]

        if len(self._datasets.keys()) == 0:
            # If the last dataset was removed, add a new one instead
            self.add_dataset()

        self.model_changed.emit()

    def change_current_dataset(self, key):
        self._current_dataset = key

    def get_datasets(self):
        return self._datasets

    def get_current_dataset(self):
        return self._current_dataset
