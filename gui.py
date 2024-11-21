""" This module contains the main method and the Gtk frontend for the
FM synthesizer.
"""
# Copyright (C) 2024  CoolGuy75562
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

import sys
import json
import jsonschema
import fm  # fm.py
from abc import abstractmethod
from abc import ABC
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3agg import \
    FigureCanvasGTK3Agg as FigureCanvas  # for figures in gtk window
from gi.repository import Gtk
import gi

gi.require_version("Gtk", "3.0")
settings = Gtk.Settings.get_default()
settings.set_property("gtk-theme-name", "Adwaita")
settings.set_property("gtk-application-prefer-dark-theme", False)

OUTPUT_XLIM = (0, fm.T[fm.PLOT_LIM])
OUTPUT_YLIM = (-1.1, 1.1)
OUTPUT_XTICKS = (0, fm.T[fm.PLOT_LIM])
OUTPUT_YTICKS = (-1, 1)
OUTPUT_COLOR = 'k'
OUTPUT_TITLE_FONTSIZE = 12
OUTPUT_CANVAS_SIZE = (600, 300)

CHAIN_XLIM = (0, fm.T[fm.PLOT_LIM])
CHAIN_YLIM = (-1.1, 1.1)
CHAIN_XTICKS = (0, fm.T[fm.PLOT_LIM])
CHAIN_YTICKS = (-1, 1)
CHAIN_COLOR = 'k'
CHAIN_TITLE_FONTSIZE = 10
CHAIN_CANVAS_SIZE = (300, 150)

ENV_XLIM = (0, fm.SECONDS)
ENV_YLIM = (0, 1.1)
ENV_YTICKS = (0, 1)
ENV_COLOR = 'k'
ENV_TITLE_FONTSIZE = 10
ENV_CANVAS_SIZE = (300, 150)

SIDEBAR_SIZE = (50, 500)
CHAIN_INPUT_SIZE = (600, 200)
ENV_INPUT_SIZE = (300, 200)

SPINBUTTON_DIGITS = {"freqs": 5, "mod_indices": 5, "feedback": 0}
SPINBUTTON_ADJUSTMENT = {
    "freqs": {
        "value": 0,
        "lower": 0,
        "upper": 100,
        "step_increment": 1,
        "page_increment": 5,
        "page_size": 0
    },
    "mod_indices": {
        "value": 0,
        "lower": 0,
        "upper": 100,
        "step_increment": 0.1,
        "page_increment": 1,
        "page_size": 0
    },
    "feedback": {
        "value": 0,
        "lower": 0,
        "upper": 10,
        "step_increment": 1,
        "page_increment": 2,
        "page_size": 0
    }
}


class AlgorithmDialog(Gtk.Dialog):
    """ Dialog for getting the number of operators per chain (algorithm).

    Attributes:
        chain_entries: A list of the spinbuttons used
            to input number of operators for respective chain.
    """
    def __init__(self):
        """ Creates and initialises "OK" button and entry spinbuttons,
        and lays them out on a grid.
        """
        super().__init__(title="set algorithm")

        self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)

        grid = Gtk.Grid()

        # set up spinbuttons
        self.chain_entries = []
        initial_vals = [2, 2, 2]
        lower_limits = [1, 0, 0]
        for i, (val, lower_limit) in enumerate(zip(initial_vals,
                                                   lower_limits)
                                               ):
            adjustment = Gtk.Adjustment(upper=5,
                                        lower=lower_limit,
                                        step_increment=1,
                                        page_increment=2
                                        )
            chain_entry = Gtk.SpinButton()
            chain_entry.set_adjustment(adjustment)
            chain_entry.set_value(val)
            chain_entry.update()
            grid.attach(chain_entry, 3*i, 0, 2, 1)
            self.chain_entries.append(chain_entry)

        box = self.get_content_area()
        box.add(grid)
        self.show_all()

    def get_algorithm(self) -> list[int]:
        """ Returns a list of the values of the entries which are nonzero """
        entry_vals = [entry.get_value_as_int()
                      for entry in self.chain_entries]
        return [val for val in entry_vals if val != 0]


class ChainWidget(Gtk.Grid):
    """ A widget containing entries for the parameters
    for each operator in a chain, and a button to update
    the chain's operator parameters to those new values.

    ChainWidget is given chain_output_plot and output_plot
    objects to update the plot when the synth is updated.

    Attributes:
        synth: The synth object
        chain_idx: Which chain in synth we are working with
        *_spinbuttons: List of spinbuttons for entry for
            respective operator parameters.
        chain_output_plot: The ChainOutputPlot object corresponding
            to chain chain_idx
        output_plot: The OutputPlot object for the main output
    """
    def __init__(self,
                 synth: fm.Synth,
                 chain_output_plot,
                 output_plot,
                 chain_idx: int,
                 ) -> None:
        """ Sets up an input grid for parameters of an individual chain.

        Args:
            synth: The synth object whose chain we are working with
            chain_ax: A reference to the chain output plot
            chain_canvas: A reference to the canvas containing
                the chain output plot
            chain_idx: Index of the chain in synth we are working with
            main_window: A reference to the main window,
                so that when a chain is modified we can
                ask the final output plot to update
        """
        super().__init__()
        self.synth = synth
        self.chain_idx = chain_idx
        self.chain_output_plot = chain_output_plot
        self.output_plot = output_plot

        # set up spinbuttons and update button
        # for entering and updating chain parameters
        update_button = Gtk.Button(label="Update Parameters")
        update_button.connect("clicked", self.on_update_button_clicked)

        def _init_chain_param_spinbuttons(param_name: str
                                          ) -> list[Gtk.SpinButton]:
            spinbuttons = []
            initial_vals = getattr(self.synth.chains[chain_idx], param_name)
            for val in initial_vals:
                spinbutton = Gtk.SpinButton()
                adjustment = Gtk.Adjustment(
                    **SPINBUTTON_ADJUSTMENT[param_name]
                )
                spinbutton.set_adjustment(adjustment)
                spinbutton.set_digits(SPINBUTTON_DIGITS[param_name])
                spinbutton.set_value(val)
                spinbuttons.append(spinbutton)
            return spinbuttons

        self.freq_spinbuttons = _init_chain_param_spinbuttons("freqs")
        self.mod_idx_spinbuttons = _init_chain_param_spinbuttons("mod_indices")
        self.feedback_spinbuttons = _init_chain_param_spinbuttons("feedback")

        volume_scale = Gtk.Scale()
        volume_adjustment = {
            "value": 0,
            "lower": 0,
            "upper": 1.0,
            "step_increment": 0.01,
            "page_increment": 0.1,
            "page_size": 0
        }
        volume_scale.set_adjustment(Gtk.Adjustment(**volume_adjustment))
        volume_scale.set_digits(2)
        volume_scale.set_value(self.synth.patch["volume"][self.chain_idx])
        volume_scale.connect("value-changed", self.on_volume_scale_changed)
        volume_scale.set_orientation(Gtk.Orientation.HORIZONTAL)
        
        # spinbuttons and update button go in a grid
        self.attach(update_button, 0, 0, 1, 1)
        self.attach(Gtk.Label(label="Frequency"), 0, 1, 1, 1)
        self.attach(Gtk.Label(label="Modulation Index"), 0, 2, 1, 1)
        self.attach(Gtk.Label(label="Feedback"), 0, 3, 1, 1)
        self.attach(Gtk.Label(label="Volume"), 0, 4, 1, 1)
        for i, (freq_sb, mi_sb, fb_sb) in enumerate(zip(
                self.freq_spinbuttons,
                self.mod_idx_spinbuttons,
                self.feedback_spinbuttons
        )):
            self.attach(freq_sb, i+1, 1, 1, 1)
            self.attach_next_to(mi_sb, freq_sb, Gtk.PositionType.BOTTOM, 1, 1)
            self.attach_next_to(fb_sb, mi_sb, Gtk.PositionType.BOTTOM, 1, 1)
            op_label = Gtk.Label(label=f"Operator {str(i+1)}")
            self.attach_next_to(op_label, freq_sb,
                                Gtk.PositionType.TOP, 1, 1)
        self.attach(volume_scale, 1, 4, 2, 1)
        
    def on_update_button_clicked(self, widget):
        """ Sets the synth parameters to the values in the entries
            and calls method to update chain and output plots.
        """
        freqs = [freq_sb.get_value() for freq_sb in self.freq_spinbuttons]
        mod_indices = [mi_sb.get_value() for mi_sb in self.mod_idx_spinbuttons]
        feedbacks = [fb_sb.get_value_as_int()
                     for fb_sb in self.feedback_spinbuttons]
        envs = self.synth.chains[self.chain_idx].envs
        self.synth.set_chain_params((freqs, mod_indices, envs, feedbacks),
                                    self.chain_idx
                                    )
        self.chain_output_plot.update_plot()
        self.output_plot.update_plot()

    def on_volume_scale_changed(self, scale):
        self.synth.set_chain_volume(scale.get_value(), self.chain_idx)
        self.chain_output_plot.update_plot()
        self.output_plot.update_plot()

        
class EnvelopeWidget(Gtk.Grid):
    """ Widget with envelope parameter entries and
        button to update output envelope to values in entries,
        and update envelope plot.
    """
    def __init__(self, synth, envelope_plot):
        super().__init__()
        self.synth = synth
        self.envelope_plot = envelope_plot

        # initialise envelope parameter headers
        env_headers = []
        env_header_labels = ["Attack", "Decay", "Sustain",
                             "Sustain Level", "Release"]
        for env_header_label in env_header_labels:
            env_header = Gtk.Label(label=env_header_label)
            env_headers.append(env_header)
        self.update_output_env_button = Gtk.Button(
            label="Update Output Envelope"
        )
        self.update_output_env_button.connect(
            "clicked",
            self.on_update_output_env_button_clicked
        )
        env_params = self.synth.get_envelope_patch_param()
        self.env_spinbuttons = []
        for val in env_params:
            env_sb = Gtk.SpinButton()
            adjustment = Gtk.Adjustment(upper=1,
                                        lower=0,
                                        step_increment=0.005,
                                        page_increment=0.1
                                        )
            env_sb.set_adjustment(adjustment)
            env_sb.set_digits(4)
            env_sb.set_value(val)
            self.env_spinbuttons.append(env_sb)

        self.attach(self.update_output_env_button, 0, 0, 1, 1)
        for i, (env_sb, env_header) in enumerate(zip(self.env_spinbuttons,
                                                     env_headers)
                                                 ):
            self.attach(env_header, 0, i+1, 1, 1)
            self.attach(env_sb, 1, i+1, 1, 1)

    def on_update_output_env_button_clicked(self, widget):
        """ Updates synth output envelope to values in
            the entries, and makes call to update the envelope plot.
        """
        output_env = [env_sb.get_value() for env_sb in self.env_spinbuttons]
        self.synth.set_output_envelope(output_env)
        self.envelope_plot.update_plot()

    def activate(self, val):
        """ Disables update button and inputs if val is False,
            enables if True.
        """
        self.update_output_env_button.set_sensitive(val)
        for button in self.env_spinbuttons:
            button.set_sensitive(val)


class Plot(ABC):

    @abstractmethod
    def update_plot(self):
        pass

    @property
    @abstractmethod
    def canvas(self):
        pass


class ChainOutputPlot(Plot):

    def __init__(self, synth, chain_idx):
        self._synth = synth
        self._chain_idx = chain_idx

        fig = Figure()
        self._canvas = FigureCanvas(fig)
        self._canvas.set_size_request(*CHAIN_CANVAS_SIZE)

        self._ax = fig.add_subplot()
        self._ax.set_xlim(*CHAIN_XLIM)
        self._ax.set_ylim(*CHAIN_YLIM)
        self._ax.set_xticks(CHAIN_XTICKS)
        self._ax.set_yticks(CHAIN_YTICKS)
        self._ax.set_title(
            f"Chain {chain_idx+1} Output",
            fontsize=CHAIN_TITLE_FONTSIZE
        )

        plot_params = self._synth.get_chain_output_plot_params(
            self._chain_idx
        )
        self._ax.plot(*plot_params, color=CHAIN_COLOR)
        fig.set_tight_layout(True)
        self._canvas.draw_idle()

    def update_plot(self):
        self._ax.lines.clear()
        plot_params = self._synth.get_chain_output_plot_params(
            self._chain_idx
        )
        self._ax.plot(*plot_params, color=CHAIN_COLOR)
        self._canvas.draw_idle()

    @property
    def canvas(self):
        return self._canvas


class EnvelopePlot(Plot):

    def __init__(self, synth):
        self._synth = synth

        fig = Figure()
        self._canvas = FigureCanvas(fig)
        self._canvas.set_size_request(*ENV_CANVAS_SIZE)

        self._ax = fig.add_subplot()
        self._ax.set_xlim(*ENV_XLIM)
        self._ax.set_ylim(*ENV_YLIM)
        self._ax.set_yticks(ENV_YTICKS)
        self._ax.set_title("Output Envelope", fontsize=ENV_TITLE_FONTSIZE)

        plot_params = self._synth.get_envelope_plot_params()
        self._ax.plot(*plot_params, color=ENV_COLOR)
        fig.set_tight_layout(True)
        self._canvas.draw_idle()

    def update_plot(self):
        self._ax.lines.clear()
        plot_params = self._synth.get_envelope_plot_params()
        self._ax.plot(*plot_params, color=ENV_COLOR)
        self._canvas.draw_idle()

    @property
    def canvas(self):
        return self._canvas


class OutputPlot(Plot):

    def __init__(self, synth):
        self._synth = synth

        fig = Figure()
        self._canvas = FigureCanvas(fig)
        self._canvas.set_size_request(*OUTPUT_CANVAS_SIZE)

        self._ax = fig.add_subplot()
        self._ax.set_xlim(*OUTPUT_XLIM)
        self._ax.set_ylim(*OUTPUT_YLIM)
        self._ax.set_xticks(OUTPUT_XTICKS)
        self._ax.set_yticks(OUTPUT_YTICKS)
        self._ax.set_title(
            "Output",
            fontsize=OUTPUT_TITLE_FONTSIZE
        )

        plot_params = self._synth.get_output_plot_params()
        self._ax.plot(*plot_params, color=OUTPUT_COLOR)
        fig.set_tight_layout(True)
        self._canvas.draw_idle()

    def update_plot(self):
        self._ax.lines.clear()
        plot_params = self._synth.get_output_plot_params()
        self._ax.plot(*plot_params, color=OUTPUT_COLOR)
        self._canvas.draw_idle()

    @property
    def canvas(self):
        return self._canvas


class MainWindow(Gtk.Window):
    """ Gtk window which provides the interface between
    the user and the Synth object synth.

    MainWindow contains three main areas, which are laid out in a Gtk.Grid:
        - A sidebar which has a play button, a save button,
              and buttons to switch the visible chain input area
              and chain plot. And a checkbox to enable or disable
              the output envelope.
        - Input areas for chains and the output envelope.
        - An output plot, plot for the current chain output,
              and output envelope plot.

    Attributes:
        synth: An fm.Synth object which is responsible for all synth
            computations and handling patch data
        envelope_plot: An EnvelopePlot object which updates the envelope
            plot in the envelope FigureCanvas when the envelope is toggled
            on/off.
        chain_plot_stack: A stack containing a plot for each chain.
            When the chain stack visible child is changed to another chain,
            the visible chain plot is changed to the respective chain.
    """
    def __init__(self, synth):
        """ We initialise plots for the output,
            chain outputs, and the output envelope,
            and set up the stacks for the chain input areas
            and the chain plots.
        We then set up the output envelope entry area,
            and finally put eveything in a grid.
        """

        super().__init__(title="FM Synthesizer")
        self.synth = synth

        # Initialise plots, chain stack, and chain stack switcher
        output_plot = OutputPlot(self.synth)
        self.envelope_plot = EnvelopePlot(self.synth)

        chain_stack = Gtk.Stack()
        self.chain_plot_stack = Gtk.Stack()
        for i in range(len(self.synth.patch["algorithm"])):
            chain_output_plot = ChainOutputPlot(self.synth, i)
            self.chain_plot_stack.add_titled(
                chain_output_plot.canvas,
                str(i),
                f"Chain {i+1}"
            )
            chain_widget = ChainWidget(
                self.synth,
                chain_output_plot,
                output_plot,
                i
            )
            chain_stack.add_titled(chain_widget, str(i), f"Chain {i+1}")

        chain_stack_switcher = Gtk.StackSwitcher()
        chain_stack_switcher.set_orientation(Gtk.Orientation.VERTICAL)
        chain_stack_switcher.set_stack(chain_stack)
        # The stack switcher can only control one stack,
        # this is to get around that.
        chain_stack.connect("notify::visible-child", self.switch_chain_plot)

        # Envelope input area
        self.envelope_widget = EnvelopeWidget(self.synth, self.envelope_plot)
        self.envelope_widget.activate(self.synth.has_output_envelope())

        # Initialise buttons and sidebar
        play_button = Gtk.Button(label="Play")
        play_button.connect("clicked", self.on_play_button_clicked)

        save_button = Gtk.Button(label="Save Patch")
        save_button.connect("clicked", self.on_save_button_clicked)

        envelope_toggle = Gtk.CheckButton(label="Output Envelope")
        envelope_toggle.connect("toggled", self.on_envelope_toggle_activated)
        envelope_toggle.set_active(self.synth.has_output_envelope())

        about_button = Gtk.Button(label="About")
        about_button.connect("clicked", self.on_about_button_clicked)

        # Sidebar
        box = Gtk.Box()
        box.set_size_request(*SIDEBAR_SIZE)
        box.set_orientation(Gtk.Orientation.VERTICAL)
        box.pack_start(play_button, True, True, 0)
        box.pack_start(save_button, True, True, 0)
        box.pack_start(chain_stack_switcher, True, True, 0)
        box.pack_start(envelope_toggle, False, False, 0)
        box.pack_start(about_button, False, False, 0)

        # Plots go in a grid
        figure_grid = Gtk.Grid()
        figure_grid.attach(output_plot.canvas, 0, 0, 2, 4)
        figure_grid.attach(self.chain_plot_stack, 2, 0, 2, 2)
        figure_grid.attach(self.envelope_plot.canvas, 2, 2, 2, 2)

        # Finally, everything gets laid out in a grid:
        grid = Gtk.Grid()

        grid.attach(box, 0, 0, 1, 5)

        chain_stack_frame = Gtk.Frame()
        chain_stack_frame.set_size_request(*CHAIN_INPUT_SIZE)
        chain_stack_frame.add(chain_stack)
        grid.attach(chain_stack_frame, 1, 0, 12, 2)

        envelope_widget_frame = Gtk.Frame()
        envelope_widget_frame.set_size_request(*ENV_INPUT_SIZE)
        envelope_widget_frame.add(self.envelope_widget)
        grid.attach(envelope_widget_frame, 13, 0, 6, 2)

        figure_grid_frame = Gtk.Frame()
        figure_grid_frame.add(figure_grid)
        grid.attach(figure_grid_frame, 1, 2, 18, 3)

        self.add(grid)
        self.set_resizable(False)

    def on_envelope_toggle_activated(self, togglebutton):
        if togglebutton.get_active():
            self.synth.set_output_envelope_to_prev()
            self.envelope_widget.activate(True)
        else:
            self.synth.set_output_envelope([])
            self.envelope_widget.activate(False)
        self.envelope_plot.update_plot()

    def on_play_button_clicked(self, widget):
        """ Plays the sound of the synth's output.

        Args:
            widget: Used for Gtk.Button.connect.
        """
        self.synth.play_sound()

    def on_save_button_clicked(self, widget):
        """ Runs a dialog for the user to name and select
        the location to save the current patch parameters
        in self.synth as a .json file. Then saves the file.
        """
        dialog = Gtk.FileChooserDialog(title="Save patch file as",
                                       parent=self,
                                       action=Gtk.FileChooserAction.SAVE
                                       )
        dialog.add_buttons(Gtk.STOCK_CANCEL,
                           Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OK,
                           Gtk.ResponseType.OK
                           )
        dialog.set_current_name("patch.json")
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            patch_filename = dialog.get_filename()
            dialog.destroy()
            self.synth.save_patch(patch_filename)
        if response == Gtk.ResponseType.CANCEL:
            dialog.destroy()

    def on_about_button_clicked(self, widget):
        dialog = Gtk.AboutDialog()
        dialog.set_program_name("fm-synth")
        dialog.set_version("0.1")
        dialog.set_copyright("(C) CoolGuy75562")
        dialog.set_comments("FM Synthesizer")
        dialog.set_website("https://github.com/CoolGuy75562/fm-synth")
        dialog.set_license_type(Gtk.License(3))
        dialog.run()
        dialog.destroy()

    def switch_chain_plot(self,
                          chain_stack: Gtk.Stack,
                          gparamstring: str
                          ) -> None:
        """ Sets the visible chain plot to corresponding to the chain stack
        selected with the chain stack switcher.
        """
        page_name = chain_stack.get_visible_child_name()
        self.chain_plot_stack.set_visible_child_name(page_name)


def read_patch_from_file() -> dict:
    """ Opens dialog to choose a patch file.
        If error reading json or json is not in the correct
        format for patch, a dialog shows the error.

        Returns patch if no errors, else None
    """
    dialog = Gtk.FileChooserDialog(title="choose a file",
                                   parent=None,
                                   action=Gtk.FileChooserAction.OPEN
                                   )
    dialog.add_buttons(Gtk.STOCK_CANCEL,
                       Gtk.ResponseType.CANCEL,
                       Gtk.STOCK_OK,
                       Gtk.ResponseType.OK
                       )
    file_filter = Gtk.FileFilter()
    file_filter.set_name("json files")
    file_filter.add_mime_type("application/json")
    dialog.add_filter(file_filter)
    file_response = dialog.run()
    patch = None
    if file_response == Gtk.ResponseType.OK:
        patch_filename = dialog.get_filename()
        dialog.destroy()
        try:
            patch = fm.read_patch(patch_filename)
        except json.JSONDecodeError:
            show_patch_error_dialog(
                f"Error decoding json: {patch_filename}"
            )
        except jsonschema.ValidationError:
            show_patch_error_dialog(
                f"Invalid patch file: {patch_filename}"
            )
    return patch


def show_patch_error_dialog(message):
    patch_error_dialog = Gtk.MessageDialog(
        transient_for=None,
        flags=0,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK,
        text="Error"
    )
    patch_error_dialog.format_secondary_text(
        message
    )
    patch_error_dialog.run()
    patch_error_dialog.destroy()


def main():
    """ Initialise patch by either specifying an algorithm from
    a dialog, or by opening an existing patch file from a file
    dialog. If there are any errors, or the dialogs are closed,
    the programme ends before starting the main window.

    The patch is used to initialise the Synth object which is given
    to the main window. Then we begin the Gtk.main loop.
    """

    option_dialog = Gtk.MessageDialog(
            transient_for=None,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="",
        )
    option_dialog.format_secondary_text(
        "Do you wish to open an existing patch?"
    )

    response = option_dialog.run()
    option_dialog.destroy()
    if response == Gtk.ResponseType.YES:  # choose patch from file
        patch = read_patch_from_file()
        if not patch:
            sys.exit(1)
    elif response == Gtk.ResponseType.NO:  # make new patch from algorithm
        dialog = AlgorithmDialog()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            algorithm = dialog.get_algorithm()
            dialog.destroy()
            if not algorithm:
                sys.exit(1)
            patch = fm.new_patch_algorithm(algorithm)
        else:  # close button clicked
            dialog.destroy()
            sys.exit(0)
    else:  # ditto
        sys.exit(0)

    synth = fm.Synth(patch)
    win = MainWindow(synth)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == '__main__':
    main()
