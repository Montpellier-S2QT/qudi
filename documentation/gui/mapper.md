# GUI mapper {#mapper}

## What is the mapper ?

The mapper is a coding tool to link the value of a GUI element to the value of the logic's variable.

##  Why is it usefull ?
A very frequent need when building UI is the need to have a QtObject, like spinbox or checkbox, matching an attribute
of the logic. 
This can be done for one spinbox by the following code:

~~~~~~~~~~~~~{.py}
self._mw.some_spinBox.setValue(self.logic().get_value())
self._mw.some_spinBox.valueChanged.connect(self.gui_value_changed)
self.logic().sigValueChanged.connect(self.update_spinBox)

    def gui_value_changed(self):
        self.logic().set_value(self._mw.some_spinBox.value())

    def update_spinBox(self):
        self._mw.some_spinBox.blockSignals(True)
        self._mw.some_spinBox.setValue(self.logic().get_value())
        self._mw.some_spinBox.blockSignals(False)
~~~~~~~~~~~~~

The UI code always follow the same steps: when A change update B, when B change update A.
To write more efficient GUI code, the mapper can be used to do the same:

~~~~~~~~~~~~~{.py}
from core.mapper import Mapper
~~~~~~~~~~~~~
~~~~~~~~~~~~~{.py}
self.mapper = Mapper()

self.mapper.add_mapping(widget=self._mw.some_spinBox, model=self.logic(),
                        model_getter='get_value', 
                        model_property_notifier='sigValueChanged',
                        model_setter='set_value',

~~~~~~~~~~~~~

The mapper can also be used to clean-up properly the connected signals at deactivation via :
*self.mapper.clear_mapping()*.

## How to use the mapper

In the simplest case, the mapper is used as in the example above.
A *self.mapper = Mapper()* object is created in the *on_activate* function, and then the mapper.add_mapper() method can 
ucalled as many time as mapped objects.

The mapper can be used on spinboxes, checkboxes, sliders, etc.

The *add_mapping* method can take references to the getter/setter or strings.
This also allows support for editing attribute of the logic directly (without getter/setter).

### The use of value conversion

To add a conversion between the mapped logic and map GUI, for example to transform slider index into values,
the following code can be used.

~~~~~~~~~~~~~{.py}
from core.mapper import Converter
~~~~~~~~~~~~~
~~~~~~~~~~~~~{.py}
class SliderConverter(Converter):
    def widget_to_model(self, value):
        return slider_values[data]

    def model_to_widget(self, value):
        return int(find_nearest_index(slider_values, value))
        
        
self.mapper.add_mapping(widget=self._mw.some_spinBox, model=self.logic(),
                    model_getter='get_value', 
                    model_property_notifier='sigValueChanged',
                    model_setter='set_value',
                    coverter=SliderConverter())
~~~~~~~~~~~~~
where in the example the function *find_nearest_index* is used :
~~~~~~~~~~~~~{.py}
def find_nearest_index(array, value):
    """ Find the index of the closest value in an array. """
    idx = np.searchsorted(array, value, side="left")
    if idx > 0 and (idx == len(array) or math.fabs(value - array[idx-1]) < math.fabs(value - array[idx])):
        return idx-1
    else:
        return idx
~~~~~~~~~~~~~

### More info

For more detail, please refer to the class documentation in *qudi/core/mapper.py*.
