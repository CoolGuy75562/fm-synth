import gi
import fm # ./fm.py
from matplotlib.backends.backend_gtk3agg import \
    FigureCanvasGTK3Agg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk

settings = Gtk.Settings.get_default()
settings.set_property("gtk-theme-name", "Numix")
settings.set_property("gtk-application-prefer-dark-theme", False)

class AlgorithmDialog(Gtk.Dialog):

    def __init__(self):
        super().__init__(title="set algorithm")
        self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)

        self.chain1_entry = Gtk.Entry()
        self.chain1_entry.set_editable(True)
        self.chain1_entry.set_text("2")
        self.chain2_entry = Gtk.Entry()
        self.chain2_entry.set_editable(True)
        self.chain2_entry.set_text("0")
        self.chain3_entry = Gtk.Entry()
        self.chain3_entry.set_editable(True)
        self.chain3_entry.set_text("0")

        grid = Gtk.Grid()
        grid.attach(self.chain1_entry, 0, 0, 2, 1)
        grid.attach(self.chain2_entry, 3, 0, 2, 1)
        grid.attach(self.chain3_entry, 6, 0, 2, 1)

        box = self.get_content_area()
        box.add(grid)
        self.show_all()

        # this seems like a convoluted way of doing it
    def run(self):
        result = super(AlgorithmDialog, self).run()
        if result == Gtk.ResponseType.OK:
             algorithm = []
             algorithm.append(int(self.chain1_entry.get_text())) if self.chain1_entry.get_text() != "0" else None
             algorithm.append(int(self.chain2_entry.get_text())) if self.chain2_entry.get_text() != "0" else None
             algorithm.append(int(self.chain3_entry.get_text())) if self.chain3_entry.get_text() != "0" else None
        return algorithm
    
class MainWindow(Gtk.Window):
    """ Gtk window which provides the interface between the user and the Synth object synth.
    
    For each synth patch parameter the window has a row of text entry boxes into which the user can type new values for the parameter,
    and an update button which tells the Synth object to update its parameters to the new values in the text entry row. 

    The window has a play button which plays the sound of the synth output.

    The window shows respective plots for the outputs of each synth chain, the added output, and the output envelope.
    The relevant plots are updated when the outputs of the synth are updated.

    Beyond some very basic input formatting, and the initial creation of the patch file if needed,
    everything to do with the synth or the patch is done by the gui's Synth object.
    E.g. MainWindow gives freqs to update to synth and synth updates the output. To plot the output one calls synth.get_output_plot_params().
    """
    def __init__(self, synth):
        super().__init__(title="pythonfm")

        if synth is None:
            """ This dialog gives you the option of opening a (.json) patch file,
            or creating a new patch which is initialised to some default values by specifying an "algorithm".
            """
            option_dialog = Gtk.MessageDialog(transient_for=self,
                                              flags=0,
                                              message_type=Gtk.MessageType.QUESTION,
                                              buttons=Gtk.ButtonsType.YES_NO,
                                              text=".",
                                              )
            option_dialog.format_secondary_text(
                "Do wish to open an existing patch?"
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
        else:
            self.synth = synth

        self.to_hide = [] # for widgets we don't want to see at start, e.g. output envelope entries if synth has no envelope
        
        # -- MAIN PATCH PARAMETERS --
        """ Here we set up the section of the window for setting the main patch parameters: freqs, mod_indices, and feedback.

        The play and save buttons are also here.
        
        """
        self.headers = [] # column headers for operator parameters
        algorithm = self.synth.get_patch_param("algorithm")
        op_count = 1
        for i in algorithm:
            for j in range(i):
                header_label = "op" + str(op_count)
                header = Gtk.Label(label=header_label)
                self.headers.append(header)
                op_count += 1
                
        # play button
        self.play_button = Gtk.Button(label="play")
        self.play_button.connect("clicked", self.on_play_button_clicked)

        #save button
        self.save_button = Gtk.Button(label="save")
        self.save_button.connect("clicked", self.on_save_button_clicked)
        
        # update freqs button
        self.update_freqs_button = Gtk.Button(label="update freqs")
        self.update_freqs_button.connect("clicked", self.on_update_freqs_button_clicked)

        # update mod_indices button
        self.update_mod_indices_button = Gtk.Button(label="update mod_indices")
        self.update_mod_indices_button.connect("clicked",
                                               self.on_update_mod_indices_button_clicked)
        
        # update feedback button
        self.update_feedback_button = Gtk.Button(label="update feedback")
        self.update_feedback_button.connect("clicked", self.on_update_feedback_button_clicked)

        # lay everything out in a grid
        # should put separators between op chains
        grid = Gtk.Grid()
        grid.attach(self.play_button, 0, 0, 1, 1)
        grid.attach(self.save_button, 1, 0, 1, 1)
        for i, header in enumerate(self.headers):
            grid.attach(header, 2*i+2, 0, 2, 1)
        grid.attach(self.update_freqs_button, 0, 1, 2, 1)
        grid.attach(self.update_mod_indices_button, 0, 2, 2, 1)
        grid.attach(self.update_feedback_button, 0, 3, 2, 1)
        self.fq_entries = self.init_entry_row("freqs")
        self.mi_entries = self.init_entry_row("mod_indices")
        self.fb_entries = self.init_entry_row("feedback")
        for i, (fqe, mie, fbe) in enumerate(zip(self.fq_entries, self.mi_entries, self.fb_entries)):
            grid.attach(fqe, 2*i+2, 1, 2, 1)
            grid.attach(mie, 2*i+2, 2, 2, 1)
            grid.attach(fbe, 2*i+2, 3, 2, 1)

        

        # initialise figures
        fig = Figure(figsize=(5, 4), dpi=100)

        n_rows = getattr(self.synth, 'n_chains') + 2

        # plots for synth output (without envelope) and output envelope
        op_ax = fig.add_subplot(n_rows, 1, n_rows-1)
        env_ax = fig.add_subplot(n_rows, 1, n_rows)
        
        output_plot_params = self.synth.get_output_plot_params()
        op_ax.plot(*output_plot_params)
        env_plot_params = self.synth.get_envelope_plot_params()
        env_ax.plot(*env_plot_params)

        # one plot for each carrier
        chain_axes = []
        for i in range(0, getattr(self.synth, 'n_chains')): 
            chain_axes.append(fig.add_subplot(n_rows, 1, i+1))
        # two loops is redundant methinks
        for i, chain_ax in enumerate(chain_axes):
            chain_ax_plot_params = self.synth.get_output_plot_params(i+1)
            chain_ax.plot(*chain_ax_plot_params)
            
        canvas = FigureCanvas(fig)
        canvas.set_size_request(400,300)

        self.fig, self.canvas = fig, canvas

        # -- ENVELOPE GRID --
        """ right now this is only to set the output envelope.

        In the future there will be a dropdown list to select the operator for which one wants to change the envelope.
        """
        output_env_grid = Gtk.Grid()

        has_output_env = self.synth.has_envelope()
        
        # headers for envelope parameters
        self.env_headers = []
        env_header_labels = ["attack", "decay", "sustain", "sus level", "release"]
        for env_header_label in env_header_labels:
            env_header = Gtk.Label(label=env_header_label)
            self.env_headers.append(env_header)
        # hide headers if no output envelope
        
        
        # toggle switch for output envelope
        output_env_switch = Gtk.Switch()
        output_env_switch.connect("notify::active", self.on_output_env_switch_activated)
        output_env_switch.set_active(has_output_env) # switch is initially "on" if patch has output envelope

        # update output_env button
        self.update_output_env_button = Gtk.Button(label="update output_env")
        self.update_output_env_button.connect("clicked", self.on_update_output_env_button_clicked)

        self.output_env_entries = self.init_envelope_entry_row(has_output_env)

        if has_output_env == False:
            self.to_hide.append(self.update_output_env_button)
            self.to_hide = self.to_hide + self.env_headers
        # attach everything to the grid
        output_env_grid.attach(output_env_switch, 0, 1, 2, 1)
        output_env_grid.attach(self.update_output_env_button, 2, 1, 2, 1)
        for i, (env_entry, env_header) in enumerate(zip(self.output_env_entries, self.env_headers)):
            output_env_grid.attach(env_entry, 2*i+4, 1, 2, 1)
            output_env_grid.attach_next_to(env_header, env_entry,  Gtk.PositionType.TOP, 2, 1) # headers go above the entries
            
        # set up box for grid, figures, and output env grid to be put into
        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation.VERTICAL)

        # from top to bottom:
        box.pack_start(grid, True, True, 0) # main grid
        box.pack_start(canvas, True, True, 0) # figures
        box.pack_start(output_env_grid, True, True, 0) # output env grid
        self.add(box)

    # returns row of entries with text initialised to value of operator parameter in patch corresponding to param_name
    def init_entry_row(self, param_name):
        vals = self.synth.get_patch_param(param_name)
        entries = []
        for i in range (0, getattr(self.synth, 'n_ops')):
            entry = Gtk.Entry()
            entry.set_editable(True)
            entry.set_text(str(vals[i]))
            entries.append(entry)
        return entries
    
    # same as init_entry_row but for envelope parameters
    def init_envelope_entry_row(self, has_env, op=0):
        env = self.synth.get_envelope_patch_param(op)
        entries = []
        for i in range(0, 5):
            entry = Gtk.Entry()
            entry.set_editable(True)
            if has_env:
                entry.set_text(str(env[i]))
            else:
                entry.set_text(str(fm.default_patch["output_env"][i]))
                self.to_hide.append(entry)
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
        freqs = [fq.get_text() for fq in self.fq_entries]
        self.synth.set_patch_param(freqs, "freqs")
        self.update_plot()
        
    def on_update_mod_indices_button_clicked(self, widget):
        mod_indices = [mi.get_text() for mi in self.mi_entries]
        self.synth.set_patch_param(mod_indices, "mod_indices")
        self.update_plot()
        
    def on_update_feedback_button_clicked(self, widget):
        feedback = [fb.get_text() for fb in self.fb_entries]
        self.synth.set_patch_param(feedback, "feedback")
        self.update_plot()

    def on_update_output_env_button_clicked(self, widget):
        output_env = [oe.get_text() for oe in self.output_env_entries]
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
        self.fig.clear()
        n_rows = getattr(self.synth, 'n_chains') + 2
        op_ax = self.fig.add_subplot(n_rows, 1, n_rows-1)
        env_ax = self.fig.add_subplot(n_rows, 1, n_rows)
        output_plot_params = self.synth.get_output_plot_params()
        op_ax.plot(*output_plot_params)

        env_plot_params = self.synth.get_envelope_plot_params()
        env_ax.plot(*env_plot_params)

        # why two loops?
        chain_axes = []
        for i in range(0, getattr(self.synth, 'n_chains')):
            chain_axes.append(self.fig.add_subplot(n_rows, 1, i+1))

        for i, chain_ax in enumerate(chain_axes):
            chain_ax_plot_params = self.synth.get_output_plot_params(i+1)
            chain_ax.plot(*chain_ax_plot_params)
        self.canvas.draw_idle()
    
def start_gui(win):
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    for widget in win.to_hide:
        widget.hide()
    Gtk.main()

