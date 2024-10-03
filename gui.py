import gi
from matplotlib.backends.backend_gtk3agg import \
    FigureCanvasGTK3Agg as FigureCanvas # for figures in gtk window
from matplotlib.figure import Figure
import fm # ./fm.py

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk

settings = Gtk.Settings.get_default()
settings.set_property("gtk-theme-name", "Numix")
settings.set_property("gtk-application-prefer-dark-theme", False)

class AlgorithmDialog(Gtk.Dialog):

    def __init__(self):
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

        # this seems like a convoluted way of doing it
    def run(self):
        result = super(AlgorithmDialog, self).run()
        if result == Gtk.ResponseType.OK:
             algorithm = []
             for entry in self.chain_entries:
                 val = entry.get_value_as_int()
                 if val != 0:
                     algorithm.append(val)
             return algorithm

class MainWindow(Gtk.Window):
    """ Gtk window which provides the interface between the user and the Synth object synth.

    For each synth patch parameter the window has a row of text entry boxes into which the user can type new values for the parameter,
    and an update button which tells the Synth object to update its parameters to the new values in the text entry row.

    The window has a play button which plays the sound of the synth output.

    The window shows respective plots for the outputs of each synth chain, the added output, and the output envelope.
    The relevant plots are updated when the outputs of the synth are updated.

Everything to do with the synth itself is done in the synth object.
    E.g. MainWindow gives freqs to update to synth and synth updates the output. To plot the output one calls synth.get_output_plot_params().
    """
    def __init__(self):
        super().__init__(title="pythonfm")


        """ This dialog gives you the option of opening a (.json) patch file,
        or creating a new patch which is initialised to some default values by specifying an "algorithm".
        """
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
            dialog = Gtk.FileChooserDialog(title="choose a file",
                                           parent=self,
                                           action=Gtk.FileChooserAction.OPEN
                                           )
            dialog.add_buttons(Gtk.STOCK_CANCEL,
                               Gtk.ResponseType.CANCEL,
                               Gtk.STOCK_OK,
                               Gtk.ResponseType.OK
                               )
            filter = Gtk.FileFilter()
            filter.set_name("json files")
            filter.add_mime_type("application/json")
            dialog.add_filter(filter) # so that file dialog only shows .json files
            file_response = dialog.run()
            if file_response == Gtk.ResponseType.OK:
                patch_filename = dialog.get_filename()
                dialog.destroy()
            patch = fm.read_patch(patch_filename)
        else: # make new patch by specifying algorithm
            dialog  = AlgorithmDialog() # get input from dialog window to set algorithm
            algorithm = dialog.run() # this is the list of nonzero values in the entries, not the dialog button id
            dialog.destroy()
            patch = fm.new_patch_algorithm(algorithm)
        self.synth = fm.Synth(patch)

        self.to_hide = [] # for widgets we don't want to see at start, e.g. output envelope entries if synth has no envelope

        # -- MAIN PATCH PARAMETERS --
        """ Here we set up the section of the window for setting the main patch parameters: freqs, mod_indices, and feedback.

        The play and save buttons are also here.

        """

        # initialise headers
        self.headers = [] # column headers for operator parameters
        algorithm = self.synth.get_patch_param("algorithm")
        op_count = 1
        for i in algorithm:
            for j in range(i):
                header_label = "op" + str(op_count)
                header = Gtk.Label(label=header_label)
                self.headers.append(header)
                op_count += 1

        # initialise play button
        self.play_button = Gtk.Button(label="play")
        self.play_button.connect("clicked", self.on_play_button_clicked)

        # initialise save button
        self.save_button = Gtk.Button(label="save")
        self.save_button.connect("clicked", self.on_save_button_clicked)

        # initialise update_freqs button
        self.update_freqs_button = Gtk.Button(label="update freqs")
        self.update_freqs_button.connect("clicked", self.on_update_freqs_button_clicked)

        # initialise update_mod_indices button
        self.update_mod_indices_button = Gtk.Button(label="update mod_indices")
        self.update_mod_indices_button.connect("clicked",
                                               self.on_update_mod_indices_button_clicked)

        # initialise update_feedback button
        self.update_feedback_button = Gtk.Button(label="update feedback")
        self.update_feedback_button.connect("clicked", self.on_update_feedback_button_clicked)

        # initialise parameter input spinbuttons
        self.fq_entries = self.init_entry_row("freqs")
        self.mi_entries = self.init_entry_row("mod_indices")
        self.fb_entries = self.init_entry_row("feedback")

        # lay everything out in a grid
        grid = Gtk.Grid()
        grid.attach(self.play_button, 0, 0, 1, 1)
        grid.attach(self.save_button, 1, 0, 1, 1)
        for i, header in enumerate(self.headers):
            grid.attach(header, 2*i+2, 0, 2, 1)
        grid.attach(self.update_freqs_button, 0, 1, 2, 1)
        grid.attach(self.update_mod_indices_button, 0, 2, 2, 1)
        grid.attach(self.update_feedback_button, 0, 3, 2, 1)
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
        """ Here we set up everything for setting the output envelope

        In the future there will be a dropdown list to set envelopes for operators.
        """
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
        output_env_switch.set_active(has_output_env) # switch is initially "on" if patch has output envelope

        # initialise update output_env button
        self.update_output_env_button = Gtk.Button(label="update output_env")
        self.update_output_env_button.connect("clicked", self.on_update_output_env_button_clicked)

        # initialise output envelope parameter entries
        self.output_env_entries = self.init_envelope_entry_row(has_output_env)
        if has_output_env == False: # hide entries and update button if no envelope
            self.to_hide.append(self.update_output_env_button)
            self.to_hide = self.to_hide + self.env_headers

        # lay out everything in a grid
        output_env_grid.attach(output_env_switch, 0, 1, 2, 1)
        output_env_grid.attach(self.update_output_env_button, 2, 1, 2, 1)
        for i, (env_entry, env_header) in enumerate(zip(self.output_env_entries, self.env_headers)):
            output_env_grid.attach(env_entry, 2*i+4, 1, 2, 1)
            output_env_grid.attach_next_to(env_header, env_entry,  Gtk.PositionType.TOP, 2, 1) # headers go above the entries

        # set up box which the parameter grid, figures, and envelope grid go into
        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation.VERTICAL)

        # from top to bottom:
        box.pack_start(grid, True, True, 0) # parameter grid
        box.pack_start(self.canvas, False, False, 0) # figures
        box.pack_start(output_env_grid, True, True, 0) # output env grid
        self.add(box)
        self.set_resizable(False)

    # returns row of entries with text initialised to value of operator parameter in patch corresponding to param_name
    def init_entry_row(self, param_name):
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
    def init_envelope_entry_row(self, has_env, op=0):
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

    # play sound
    def on_play_button_clicked(self, widget):
        self.synth.play_sound()

    def on_save_button_clicked(self, widged):
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

    # update buttons get parameter values from their row of entries and send to synth object, then everything updated.
    def on_update_freqs_button_clicked(self, widget):
        freqs = [fq.get_value() for fq in self.fq_entries]
        self.synth.set_patch_param(freqs, "freqs")
        self.update_plot()

    def on_update_mod_indices_button_clicked(self, widget):
        mod_indices = [mi.get_value() for mi in self.mi_entries]
        self.synth.set_patch_param(mod_indices, "mod_indices")
        self.update_plot()

    def on_update_feedback_button_clicked(self, widget):
        feedback = [fb.get_value_as_int() for fb in self.fb_entries]
        self.synth.set_patch_param(feedback, "feedback")
        self.update_plot()

    def on_update_output_env_button_clicked(self, widget):
        output_env = [oe.get_value() for oe in self.output_env_entries]
        self.synth.set_patch_param(output_env, "output_env")
        self.update_plot()

    def on_output_env_switch_activated(self, switch, gparam):
        if switch.get_active() == True:
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

    # updates all the plots to current information in synth object.
    # this should be split into seperate functions for envelopes and outputs
    def update_plot(self):
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

        chain_axes = []
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
    win = MainWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    for widget in win.to_hide:
        widget.hide()
    Gtk.main()

if __name__ == '__main__':
    main()
