""" This module contains the main method and the Gtk frontend for the
FM synthesizer.
"""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from matplotlib.backends.backend_gtk3agg import \
    FigureCanvasGTK3Agg as FigureCanvas # for figures in gtk window
from matplotlib.figure import Figure

import fm # ./fm.py

settings = Gtk.Settings.get_default()
settings.set_property("gtk-theme-name", "Numix")
settings.set_property("gtk-application-prefer-dark-theme", False)

class AlgorithmDialog(Gtk.Dialog):
    """ Gtk dialog for user to enter number of operators per chain.

    Attributes:
        chain_entries: A list of the dialog's spinbuttons for input.
    """
    def __init__(self):
        """ Creates and initialises "OK" button and spinbuttons,
        and lays them out on a grid.
        """
        super().__init__(title="set algorithm")
        self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)

        grid = Gtk.Grid()
        self.chain_entries = []
        initial_vals = [2, 2, 2]
        lower_limits = [1, 0, 0] # this will ensure that there will be at least one operator
        for i, (val, lower_limit) in enumerate(zip(initial_vals, lower_limits)):
            adjustment = Gtk.Adjustment(upper=5, lower=lower_limit,
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

    def get_algorithm(self):
        """ Returns a list of the nonzero values of the entries. """
        entry_vals = [entry.get_value_as_int()
                      for entry in self.chain_entries]
        return [val for val in entry_vals if val != 0]



class MainWindow(Gtk.Window):
    """ Gtk window which provides the interface between the user and the Synth
    object synth, and is also responsible for choosing the synth patch parameter.

    MainWindow has three main sections that are each placed in a vbox.
    From top to bottom these are:
       - A Gtk.Grid which contains inputs for the freqs, mod_indices, and feedback
         parameters, as well as a "play" button and a "save" button.
       - A FigureCanvas which contains plots of the outputs of each chain,
         the synth output without the output envelope, and the output envelope.
       - A Gtk.Grid which contains a toggle switch, which when turned on
         has inputs for output envelope parameters.

    Attributes:
        synth: An fm.Synth object which contains patch information and is
            responsible for computing the synth output, etc.
        to_hide: A list of widgets that will be hidden
            when the window first appears.
        fq_entries: A list of spinbuttons for entry of freq parameter,
            one for each operator.
        mi_entries: Ditto for mod_indices.
        fb_entries: Ditto for feedback.
        fig: The figure which all the plots go onto.
        canvas: The FigureCanvas which fig goes into.
        env_headers: A list of Gtk.Labels with the respective text
            "attack", "decay", "sus_length", "sus_level", "release"
        update_output_env_button: Updates output env in synth to new values. Hidden if
            output_env_switch is in the "off" position.
        output_env_entries: Entries for output envelope parameters. Hidden if
            output_env_switch is in the "off" position.
    """
    def __init__(self):
        """ First initialises synth patch data, either by reading a
        patch file, or getting an algorithm parameter from a dialog.
        Then creates and initialises all the buttons, entries, and
        plots in the way described in the class docstring.

        The number of inputs and plots on the screen depends on the
        number of operators, which is determened by the Synth object's
        algorithm parameter. For instance if algorithm = [2, 2, 2] we will
        have 2 + 2 + 2 = 6 operator parameter inputs, and len(algorithm) = 3
        chain output plots. Similarly if algorithm = [1, 2] we will have
        3 parameter inputs and 2 chain output plots.
        """

        super().__init__(title="pythonfm")
        option_dialog = Gtk.MessageDialog(transient_for=self,
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
        if response == Gtk.ResponseType.YES: # choose patch from file
            patch = self._read_patch_from_file()
        else: # make new patch by specifying algorithm
            dialog  = AlgorithmDialog() # get input from dialog window to set algorithm
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                algorithm = dialog.get_algorithm()
                dialog.destroy()
            patch = fm.new_patch_algorithm(algorithm)
        self.synth = fm.Synth(patch)

        self.to_hide = [] # for widgets we don't want to see at start

        # -- MAIN PATCH PARAMETERS --
        # initialise headers
        headers = self._init_entry_headers()

        # initialise buttons
        play_button = self._init_main_button("play")
        save_button = self._init_main_button("save")
        update_freqs_button = self._init_main_button("update freqs")
        update_mod_indices_button = self._init_main_button("update mod_indices")
        update_feedback_button = self._init_main_button("update feedback")

        # initialise parameter input spinbuttons
        self.fq_entries = self._init_entry_row("freqs")
        self.mi_entries = self._init_entry_row("mod_indices")
        self.fb_entries = self._init_entry_row("feedback")

        # lay everything out in a grid
        grid = Gtk.Grid()
        grid.attach(play_button, 0, 0, 1, 1)
        grid.attach(save_button, 1, 0, 1, 1)
        for i, header in enumerate(headers):
            grid.attach(header, 2*i+2, 0, 2, 1)
        grid.attach(update_freqs_button, 0, 1, 2, 1)
        grid.attach(update_mod_indices_button, 0, 2, 2, 1)
        grid.attach(update_feedback_button, 0, 3, 2, 1)
        for i, (fqe, mie, fbe) in enumerate(zip(self.fq_entries,
                                                self.mi_entries,
                                                self.fb_entries
                                                )
                                            ):

            grid.attach(fqe, 2*i+2, 1, 2, 1)
            grid.attach(mie, 2*i+2, 2, 2, 1)
            grid.attach(fbe, 2*i+2, 3, 2, 1)

        # -- FIGURES --

        # initialise figures
        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.set_size_request(500, 500)
        self.update_plot()

        # -- ENVELOPE GRID --
        output_env_grid = Gtk.Grid()

        has_output_env = self.synth.has_envelope()

        # initialise envelope parameter headers
        self.env_headers = []
        env_header_labels = ["attack", "decay", "sustain", "sus level", "release"]
        for env_header_label in env_header_labels:
            env_header = Gtk.Label(label=env_header_label)
            self.env_headers.append(env_header) # hide headers if no output envelope

        # initialise toggle switch for output envelope
        output_env_switch = Gtk.Switch()
        output_env_switch.connect("notify::active", self.on_output_env_switch_activated)
        output_env_switch.set_active(has_output_env) # on if has output envelope

        # initialise update output_env button
        self.update_output_env_button = Gtk.Button(label="update output_env")
        self.update_output_env_button.connect("clicked", self.on_update_output_env_button_clicked)

        # initialise output envelope parameter entries
        self.output_env_entries = self._init_envelope_entry_row(has_output_env)
        if not has_output_env: # hide entries and update button if no envelope
            self.to_hide.append(self.update_output_env_button)
            self.to_hide = self.to_hide + self.env_headers

        # lay out everything in a grid
        output_env_grid.attach(output_env_switch, 0, 1, 2, 1)
        output_env_grid.attach(self.update_output_env_button, 2, 1, 2, 1)
        for i, (env_entry, env_header) in enumerate(zip(self.output_env_entries, self.env_headers)):
            output_env_grid.attach(env_entry, 2*i+4, 1, 2, 1)
            output_env_grid.attach_next_to(env_header,
                                           env_entry,
                                           Gtk.PositionType.TOP,
                                           2, 1)

        # set up box which the parameter grid, figures, and envelope grid go into
        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation.VERTICAL)

        # from top to bottom:
        box.pack_start(grid, True, True, 0) # parameter grid
        box.pack_start(self.canvas, False, False, 0) # figures
        box.pack_start(output_env_grid, True, True, 0) # output env grid
        self.add(box)
        self.set_resizable(False)

    def _read_patch_from_file(self):
        dialog = Gtk.FileChooserDialog(title="choose a file",
                                       parent=self,
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
        dialog.add_filter(file_filter) # so that file dialog only shows .json files
        file_response = dialog.run()
        if file_response == Gtk.ResponseType.OK:
            patch_filename = dialog.get_filename()
            dialog.destroy()
        return fm.read_patch(patch_filename)

    def _init_entry_headers(self):
        headers = []
        algorithm = self.synth.get_patch_param("algorithm")
        op_count = 1
        for i in algorithm:
            for _ in range(i):
                header_label = "op" + str(op_count)
                header = Gtk.Label(label=header_label)
                headers.append(header)
                op_count += 1
        return headers

    def _init_main_button(self, button_name):
        button_dict = {"play" : self.on_play_button_clicked,
                       "save" : self.on_save_button_clicked,
                       "update freqs" : self.on_update_freqs_button_clicked,
                       "update mod_indices" : self.on_update_mod_indices_button_clicked,
                       "update feedback" : self.on_update_feedback_button_clicked
                       }
        button = Gtk.Button(label=button_name)
        button.connect("clicked", button_dict[button_name])
        return button

    def _init_entry_row(self, param_name):
        # Gtk.Adjustment parameters in first entry, digits in second entry
        sb_settings = {"freqs" : ([0, 0, 100, 1, 5, 0], 5),
                       "mod_indices" : ([0, 0, 100, 0.1, 1, 0], 5),
                       "feedback" : ([0, 0, 10, 1, 2, 0], 0)
                       }
        vals = self.synth.get_patch_param(param_name)
        entries = []
        n_ops = sum(self.synth.get_patch_param("algorithm"))
        for i in range(n_ops):
            entry = Gtk.SpinButton()
            adjustment = Gtk.Adjustment(*sb_settings[param_name][0])
            entry.set_adjustment(adjustment)
            entry.set_digits(sb_settings[param_name][1])
            entry.set_value(vals[i])
            entries.append(entry)
        return entries

    # same as init_entry_row but for envelope parameters
    def _init_envelope_entry_row(self, has_env, op=0):
        env_params = self.synth.get_envelope_patch_param(op)
        entries = []
        initial_vals = env_params if has_env else fm.default_patch["output_env"]
        for initial_val in initial_vals:
            entry = Gtk.SpinButton()
            adjustment = Gtk.Adjustment(upper=1,
                                        lower=0,
                                        step_increment=0.005,
                                        page_increment=0.1
                                        )
            entry.set_adjustment(adjustment)
            entry.set_digits(4)
            if not has_env:
                self.to_hide.append(entry)
            entry.set_value(initial_val)
            entries.append(entry)
        return entries

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

        Args:
            widget: Used for Gtk.Button.connect.
        """
        dialog = Gtk.FileChooserDialog(title="save patch file as",
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

    def on_update_freqs_button_clicked(self, widget):
        """ Gives the values in the freq parameter entry row to synth to update,
        And updates the plot to the new synth output.

        Args:
            widget: Used for Gtk.Button.connect.
        """
        freqs = [fq.get_value() for fq in self.fq_entries]
        self.synth.set_patch_param(freqs, "freqs")
        self.update_plot()

    def on_update_mod_indices_button_clicked(self, widget):
        """ Gives the values in the mod_indices parameter entry row to synth to update,
        And updates the plot to the new synth output.

        Args:
            widget: Used for Gtk.Button.connect.
        """
        mod_indices = [mi.get_value() for mi in self.mi_entries]
        self.synth.set_patch_param(mod_indices, "mod_indices")
        self.update_plot()

    def on_update_feedback_button_clicked(self, widget):
        """ Gives the values in the feedback parameter entry row to synth to update,
        And updates the plot to the new synth output.

        Args:
            widget: Used for Gtk.Button.connect.
        """
        feedback = [fb.get_value_as_int() for fb in self.fb_entries]
        self.synth.set_patch_param(feedback, "feedback")
        self.update_plot()

    def on_update_output_env_button_clicked(self, widget):
        """ Gives the values in the output_env parameter entry row to synth to update,
        And updates the plot to the new synth output.

        Args:
            widget: Used for Gtk.Button.connect.
        """
        output_env = [oe.get_value() for oe in self.output_env_entries]
        self.synth.set_patch_param(output_env, "output_env")
        self.update_plot()

    def on_output_env_switch_activated(self, switch, gparam):
        """ Shows envelope entries, update envelope button, and header
        if switch is turned on. Hides envelope entries, update envelope button,
        and headers if switch is turned off, and updates synth to not use
        an output envelope.

        Note that turning the switch on does not update the synth's output
        envelope. You have to press the update output envelope button.

        Args:
            switch: The switch object.
            gparam: Not sure.
        """
        if switch.get_active() is True:
            # shows entries, button, and header, but does not apply envelope
            self.update_output_env_button.show()
            for entry, header in zip(self.output_env_entries, self.env_headers):
                entry.show()
                header.show()
        else:
            # hides entries, button, and header, and turns off envelope in patch
            self.update_output_env_button.hide()
            self.synth.set_patch_param(1, "output_env")
            self.update_plot()
            for entry, header in zip(self.output_env_entries, self.env_headers):
                entry.hide()
                header.hide()

    def update_plot(self):
        """ Updates the plots in self.fig to current patch data in self.synth. """
        small = 10

        self.fig.clear()
        n_chains = len(getattr(self.synth, 'chains'))
        n_rows = n_chains + 2
        op_ax = self.fig.add_subplot(n_rows, 1, n_rows-1)
        output_plot_params = self.synth.get_output_plot_params()
        op_ax.plot(*output_plot_params, clip_on=False)
        op_ax.set_xlim(0, fm.T[441])
        op_ax.set_xticks((0,fm.T[441]))
        op_ax.set_ylim(-1.1, 1.1)
        op_ax.set_yticks((-1, 1))
        op_ax.set_title("Total Output", fontsize=small)


        env_ax = self.fig.add_subplot(n_rows, 1, n_rows)
        env_plot_params = self.synth.get_envelope_plot_params()
        env_ax.plot(*env_plot_params)
        env_ax.set_xlim(0, 1)
        env_ax.set_ylim(0, 1.1)
        env_ax.set_yticks((0, 1))
        env_ax.set_title("Output Envelope", fontsize=small)

        for i in range(n_chains):
            chain_ax = self.fig.add_subplot(n_rows, 1, i+1)
            chain_ax_plot_params = self.synth.get_output_plot_params(i+1)
            chain_ax.plot(*chain_ax_plot_params)
            chain_ax.set_xlim(0, fm.T[441])
            chain_ax.set_xticks((0, fm.T[441]))
            chain_ax.set_ylim(-1.1, 1.1)
            chain_ax.set_yticks((-1, 1))
            chain_ax.set_title(f"Chain {i+1} Output", fontsize=small)

        self.fig.tight_layout()
        self.canvas.draw_idle()

def main():
    """ Sets up the main window, then begins Gtk.main() loop. """
    win = MainWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    for widget in win.to_hide:
        widget.hide()
    Gtk.main()

if __name__ == '__main__':
    main()
