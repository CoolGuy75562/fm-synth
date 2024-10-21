""" This module contains the main method and the Gtk frontend for the
FM synthesizer.
"""
import fm # ./fm.py

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from matplotlib.backends.backend_gtk3agg import \
    FigureCanvasGTK3Agg as FigureCanvas # for figures in gtk window
from matplotlib.figure import Figure

settings = Gtk.Settings.get_default()
settings.set_property("gtk-theme-name", "Numix")
settings.set_property("gtk-application-prefer-dark-theme", False)

sb_digits = {"freqs" : 5,
             "mod_indices" : 5,
             "feedback" : 0
             }

sb_adjustment = {"freqs" : {"value" : 0,
                            "lower" : 0,
                            "upper" : 100,
                            "step_increment" : 1,
                            "page_increment" : 5,
                            "page_size" : 0
                            },
                 "mod_indices" : {"value" : 0,
                                  "lower" : 0,
                                  "upper" : 100,
                                  "step_increment" : 0.1,
                                  "page_increment" : 1,
                                  "page_size" : 0
                                  },
                 "feedback" : {"value" : 0,
                               "lower" : 0,
                               "upper" : 10,
                               "step_increment" : 1,
                               "page_increment" : 2,
                               "page_size" : 0
                               }
                 }

sb_settings = {"freqs" : ([0, 0, 100, 1, 5, 0], 5),
               "mod_indices" : ([0, 0, 100, 0.1, 1, 0], 5),
               "feedback" : ([0, 0, 10, 1, 2, 0], 0)
               }

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


class ChainWidget(Gtk.Box):
    """ Section of mainwindow which shows information about the given chain """
    def __init__(self, synth, chain_ax, chain_canvas, chain_idx, main_window):
        super().__init__()
        self.synth = synth
        self.chain_idx = chain_idx
        self.main_window = main_window
        
        # set up spinbuttons and update button for entering and updating chain parameters
        self.update_button = Gtk.Button(label="update parameters")
        self.update_button.connect("clicked", self.on_update_button_clicked)

        def _init_chain_param_spinbuttons(param_name):
            spinbuttons = []
            initial_vals = getattr(self.synth.chains[chain_idx], param_name)
            for val in initial_vals:
                spinbutton = Gtk.SpinButton()
                adjustment = Gtk.Adjustment(**sb_adjustment[param_name])
                spinbutton.set_adjustment(adjustment)
                spinbutton.set_digits(sb_digits[param_name])
                spinbutton.set_value(val)
                spinbuttons.append(spinbutton)
            return spinbuttons

        self.freq_spinbuttons = _init_chain_param_spinbuttons("freqs")
        self.mod_idx_spinbuttons = _init_chain_param_spinbuttons("mod_indices")
        self.feedback_spinbuttons = _init_chain_param_spinbuttons("feedback")
        param_names = ["freqs", "mod_indices", "feedback"]
        self.chain_param_labels = [Gtk.Label(label=param_name) for param_name in param_names]

        self.chain_ax, self.chain_canvas = chain_ax, chain_canvas

        # spinbuttons and update button go in a grid
        grid = Gtk.Grid()
        grid.attach(self.update_button, 0, 0, 2, 1)
        grid.attach(self.chain_param_labels[0], 0, 1, 2, 1)
        grid.attach(self.chain_param_labels[1], 0, 2, 2, 1)
        grid.attach(self.chain_param_labels[2], 0, 3, 2, 1)
        for i, (freq_sb, mi_sb, fb_sb) in enumerate(zip(self.freq_spinbuttons,
                                                        self.mod_idx_spinbuttons,
                                                        self.feedback_spinbuttons)):
            grid.attach(freq_sb, 2*i+2, 1, 2, 1)
            grid.attach_next_to(mi_sb, freq_sb, Gtk.PositionType.BOTTOM, 2, 1)
            grid.attach_next_to(fb_sb, mi_sb, Gtk.PositionType.BOTTOM, 2, 1)

        self.pack_start(grid, True, True, 0)

        
    def on_update_button_clicked(self, widget):
        freqs = [freq_sb.get_value() for freq_sb in self.freq_spinbuttons]
        mod_indices = [mi_sb.get_value() for mi_sb in self.mod_idx_spinbuttons]
        feedbacks = [fb_sb.get_value_as_int() for fb_sb in self.feedback_spinbuttons]
        envs = self.synth.chains[self.chain_idx].envs
        self.synth.set_chain_params((freqs, mod_indices, envs, feedbacks), self.chain_idx)
        self.update_chain_plot()

    def update_chain_plot(self):
        self.chain_ax.lines.clear()
        chain_plot_params = self.synth.get_chain_output_plot_params(self.chain_idx)
        self.chain_ax.plot(*chain_plot_params, color='k')
        self.chain_canvas.draw_idle()
        self.main_window.update_plot() # not ideal
        
class EnvelopeWidget(Gtk.Box):
    """ Box which holds entries and plot for output envelope.
    In the future this will also be able to deal with envelopes of individual operators.
    """
    def __init__(self, synth, env_ax, env_canvas):
        super().__init__()
        self.synth = synth

        # initialise envelope plot
        self.env_ax, self.env_canvas = env_ax, env_canvas

        # initialise envelope parameter headers
        env_headers = []
        env_header_labels = ["attack", "decay", "sustain", "sus level", "release"]
        for env_header_label in env_header_labels:
            env_header = Gtk.Label(label=env_header_label)
            env_headers.append(env_header)
        self.update_output_env_button = Gtk.Button(label="update output_env")
        self.update_output_env_button.connect("clicked", self.on_update_output_env_button_clicked)

        env_params = self.synth.get_envelope_patch_param() # default patch envelope params if no env
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

        # put labels and entries in grid
        output_env_grid = Gtk.Grid()
        output_env_grid.attach(self.update_output_env_button, 2, 1, 2, 1)
        for i, (env_sb, env_header) in enumerate(zip(self.env_spinbuttons, env_headers)):
            output_env_grid.attach(env_sb, 2*i+4, 1, 2, 1)
            output_env_grid.attach_next_to(env_header,
                                           env_sb,
                                           Gtk.PositionType.TOP,
                                           2, 1)
        self.pack_start(output_env_grid, True, True, 0)

    def on_update_output_env_button_clicked(self, widget):
        output_env = [env_sb.get_value() for env_sb in self.env_spinbuttons]
        self.synth.set_output_env(output_env)
        self.update_plot()

    def update_plot(self):
        self.env_ax.lines.clear()
        env_plot_params = self.synth.get_envelope_plot_params()
        self.env_ax.plot(*env_plot_params, color='k')
        self.env_canvas.draw_idle()
        
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


        # initialise plots:

        fig = Figure()
        self.output_canvas = FigureCanvas(fig)
        self.output_canvas.set_size_request(600, 150)
        self.output_ax = fig.add_subplot(111)
        self.output_ax.set_xlim(0, fm.T[441])
        self.output_ax.set_ylim(-1.1, 1.1)
        self.output_ax.set_xticks((0, fm.T[441]))
        self.output_ax.set_yticks((-1, 1))
        self.output_ax.set_title("Output", fontsize=12)
        output_plot_params = self.synth.get_output_plot_params()
        self.output_ax.plot(*output_plot_params, color='k')
        
        fig = Figure()
        output_env_canvas = FigureCanvas(fig)
        output_env_canvas.set_size_request(400, 150)
        env_ax = fig.add_subplot(111)
        env_ax.set_xlim(0, 1)
        env_ax.set_ylim(0,1.1)
        env_ax.set_yticks((0,1))
        env_ax.set_title("Output Envelope", fontsize=10)
        env_plot_params = self.synth.get_envelope_plot_params()
        env_ax.plot(*env_plot_params, color='k')
        output_env_canvas.draw_idle()
        
        def _init_chain_plot(chain_idx):
            fig = Figure()
            chain_canvas = FigureCanvas(fig)
            chain_canvas.set_size_request(400, 150)
            chain_ax = fig.add_subplot(111)
            chain_ax.set_xlim(0, fm.T[441])
            chain_ax.set_ylim(-1.1, 1.1)
            chain_ax.set_xticks((0, fm.T[441]))
            chain_ax.set_yticks((-1, 1))
            chain_ax.set_title(f"Chain {chain_idx+1} Output", fontsize=10)
            chain_ax_plot_params = self.synth.get_chain_output_plot_params(chain_idx)
            chain_ax.plot(*chain_ax_plot_params, color='k')
            chain_canvas.draw_idle()
            return chain_ax, chain_canvas

        self.chain_axes = []
        self.chain_canvases = []
        self.chain_plot_stack = Gtk.Stack()
        for i in range(len(self.synth.patch["algorithm"])):
            chain_ax, chain_canvas = _init_chain_plot(i)
            self.chain_plot_stack.add_titled(chain_canvas, str(i), f"Chain {i+1}")
            self.chain_axes.append(chain_ax)
            self.chain_canvases.append(chain_canvas)
            
        self.chainwidgets = []
        self.chain_stack = Gtk.Stack()
        for i in range(len(self.synth.patch["algorithm"])):
            chain_widget = ChainWidget(self.synth, self.chain_axes[i], self.chain_canvases[i], i, self)
            self.chainwidgets.append(chain_widget)
            self.chain_stack.add_titled(chain_widget, str(i), f"Chain {i+1}")
            
        self.chain_stack_switcher = Gtk.StackSwitcher()
        self.chain_stack_switcher.set_orientation(Gtk.Orientation.VERTICAL)
        self.chain_stack_switcher.set_stack(self.chain_stack)
        self.chain_stack.connect("notify::visible-child", self.switch_chain_plot)
        
        # initialise buttons
        play_button = Gtk.Button(label="play")
        play_button.connect("clicked", self.on_play_button_clicked)
        save_button = Gtk.Button(label="save")
        save_button.connect("clicked", self.on_save_button_clicked)

        

        # -- ENVELOPE GRID --
        envelope_widget = EnvelopeWidget(self.synth, env_ax, output_env_canvas)
        

        # set up box which the parameter grid, figures, and envelope grid go into
        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation.VERTICAL)
        box.pack_start(play_button, True, True, 0)
        box.pack_start(save_button, True, True, 0)
        box.pack_start(self.chain_stack_switcher, True, True, 0)
        
        figure_grid = Gtk.Grid()
        figure_grid.attach(self.output_canvas, 0, 0, 2, 4)
        figure_grid.attach(self.chain_plot_stack, 2, 0, 2, 2)
        figure_grid.attach(output_env_canvas, 2, 2, 2, 2)
        
        # lay everything out in a grid
        grid = Gtk.Grid()
        grid.attach(box, 0, 0, 1, 3)
        grid.attach_next_to(self.chain_stack, box, Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(envelope_widget, self.chain_stack, Gtk.PositionType.BOTTOM, 1, 1)
        grid.attach_next_to(figure_grid, envelope_widget, Gtk.PositionType.BOTTOM, 3, 3)
        
        self.add(grid)
        self.set_resizable(False)

    def switch_chain_plot(self, chain_stack, gparamstring):
        page_name = chain_stack.get_visible_child_name()
        self.chain_plot_stack.set_visible_child_name(page_name)
        
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

    def update_plot(self):
        self.output_ax.lines.clear()
        output_plot_params = self.synth.get_output_plot_params()
        self.output_ax.plot(*output_plot_params, color='k')
        self.output_canvas.draw_idle()

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
