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
from matplotlib.axes import Axes

settings = Gtk.Settings.get_default()
settings.set_property("gtk-theme-name", "Numix")
settings.set_property("gtk-application-prefer-dark-theme", False) # turn off dark mode

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
    """ Dialog for getting the number of operators per chain (algorithm).

    Attributes:
        chain_entries: A list of the spinbuttons used to input number of operators
            for respective chain.
    """
    def __init__(self):
        """ Creates and initialises "OK" button and entry spinbuttons,
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

    def get_algorithm(self) -> list[int]:
        """ Returns a list of the values of the entries which are nonzero """
        entry_vals = [entry.get_value_as_int()
                      for entry in self.chain_entries]
        return [val for val in entry_vals if val != 0]


class ChainWidget(Gtk.Grid):
    """ A grid containing entries for the parameters for each operator in a chain,
    and a button to update the chain's operator parameters to those new values. 

    ChainWidget is passed a reference to the chain output plot, so that when the
    chain parameters are updated, the chain output plot is updated. Similarly
    it is given a reference to the main window so that it can tell the main window
    to update the output plot when a chain's output changes.

    Attributes:
        synth: The synth object
        chain_idx: Which chain in synth we are working with
        main_window: The main window
        *_spinbuttons: List of spinbuttons for entry for respective operator parameters.
        chain_canvas: The canvas containing the chain output plot
        chain_ax: The Axes object for the chain output plot
    """
    def __init__(self, synth: fm.Synth, chain_ax: Axes, chain_canvas: FigureCanvas, chain_idx: int, main_window: Gtk.Window) -> None:
        """ Sets up an input grid for parameters of an individual chain.

        Args:
            synth: The synth object whose chain we are working with
            chain_ax: A reference to the chain output plot
            chain_canvas: A reference to the canvas containing the chain output plot
            chain_idx: Index of the chain in synth we are working with
            main_window: A reference to the main window, so that when a chain is modified
                we can ask the final output plot to update
        """
        super().__init__()
        self.synth = synth
        self.chain_idx = chain_idx
        self.main_window = main_window
        
        # set up spinbuttons and update button for entering and updating chain parameters
        update_button = Gtk.Button(label="update parameters")
        update_button.connect("clicked", self.on_update_button_clicked)

        def _init_chain_param_spinbuttons(param_name: str) -> list[Gtk.SpinButton]:
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
        chain_param_labels = [Gtk.Label(label=param_name) for param_name in param_names]

        self.chain_ax, self.chain_canvas = chain_ax, chain_canvas

        # spinbuttons and update button go in a grid
        self.attach(update_button, 0, 0, 1, 1)
        self.attach(chain_param_labels[0], 0, 1, 1, 1)
        self.attach(chain_param_labels[1], 0, 2, 1, 1)
        self.attach(chain_param_labels[2], 0, 3, 1, 1)
        for i, (freq_sb, mi_sb, fb_sb) in enumerate(zip(self.freq_spinbuttons,
                                                        self.mod_idx_spinbuttons,
                                                        self.feedback_spinbuttons)):
            self.attach(freq_sb, i+1, 1, 1, 1)
            self.attach_next_to(mi_sb, freq_sb, Gtk.PositionType.BOTTOM, 1, 1)
            self.attach_next_to(fb_sb, mi_sb, Gtk.PositionType.BOTTOM, 1, 1)


        
    def on_update_button_clicked(self, widget):
        freqs = [freq_sb.get_value() for freq_sb in self.freq_spinbuttons]
        mod_indices = [mi_sb.get_value() for mi_sb in self.mod_idx_spinbuttons]
        feedbacks = [fb_sb.get_value_as_int() for fb_sb in self.feedback_spinbuttons]
        envs = self.synth.chains[self.chain_idx].envs
        self.synth.set_chain_params((freqs, mod_indices, envs, feedbacks), self.chain_idx)
        self.update_chain_plot()

    def update_chain_plot(self) -> None:
        self.chain_ax.lines.clear()
        chain_plot_params = self.synth.get_chain_output_plot_params(self.chain_idx)
        self.chain_ax.plot(*chain_plot_params, color='k')
        self.chain_canvas.draw_idle()
        self.main_window.update_plot()
        
class EnvelopeWidget(Gtk.Grid):
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
        update_output_env_button = Gtk.Button(label="update output_env")
        update_output_env_button.connect("clicked", self.on_update_output_env_button_clicked)

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

        self.attach(update_output_env_button, 0, 0, 1, 1)
        for i, (env_sb, env_header) in enumerate(zip(self.env_spinbuttons, env_headers)):
            self.attach(env_header, 0, i+1, 1, 1)
            self.attach(env_sb, 1, i+1, 1, 1)

    def on_update_output_env_button_clicked(self, widget):
        output_env = [env_sb.get_value() for env_sb in self.env_spinbuttons]
        self.synth.set_output_env(output_env)
        self.update_plot()

    def update_plot(self) -> None:
        self.env_ax.lines.clear()
        env_plot_params = self.synth.get_envelope_plot_params()
        self.env_ax.plot(*env_plot_params, color='k')
        self.env_canvas.draw_idle()
        
class MainWindow(Gtk.Window):
    """ Gtk window which provides the interface between the user and the Synth
    object synth, and is also responsible for choosing the synth patch parameter.

    MainWindow contains three main areas, which are laid out in a Gtk.Grid:
        - A sidebar which has a play button, a save button, and buttons to switch
          the visible chain input area and chain plot.
        - Input areas for chains and the output envelope.
        - An output plot, plot for the current chain output, and output envelope plot.

    Attributes:
        synth: An fm.Synth object which is responsible for all synth computations
            and handling patch data
        output_ax: The Axes object containing the output plot.
        output_canvas: The FigureCanvas containing output_ax.
        chain_plot_stack: A stack containing a plot for each chain.
            When the chain stack visible child is changed to another chain,
            the visible chain plot is changed to the respective chain.
    """
    def __init__(self):
        """ First we initialise the Synth object, either with an existing patch
            read from a json file, or by creating a new patch initialised to some
            default values by specifying the desired number of chains and operators.

        We then initialise plots for the output, chain outputs, and the output envelope,
        and set up the stacks for the chain input areas and the chain plots.
        We then set up the output envelope entry area, and finally put eveything in a grid.
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


        # -- Initialise Figures, Chain Stacks, and Chain Stack Switcher --

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
        
        def _init_chain_plot(chain_idx: int) -> tuple[Axes, FigureCanvas]:
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

        chain_axes = []
        chain_canvases = []
        chain_stack = Gtk.Stack()
        self.chain_plot_stack = Gtk.Stack()
        for i in range(len(self.synth.patch["algorithm"])):
            chain_ax, chain_canvas = _init_chain_plot(i)
            self.chain_plot_stack.add_titled(chain_canvas, str(i), f"Chain {i+1}")
            chain_widget = ChainWidget(self.synth, chain_ax, chain_canvas, i, self)
            chain_stack.add_titled(chain_widget, str(i), f"Chain {i+1}")
            
        chain_stack_switcher = Gtk.StackSwitcher()
        chain_stack_switcher.set_orientation(Gtk.Orientation.VERTICAL)
        chain_stack_switcher.set_stack(chain_stack)
        chain_stack.connect("notify::visible-child", self.switch_chain_plot)
        
        # initialise buttons
        play_button = Gtk.Button(label="play")
        play_button.connect("clicked", self.on_play_button_clicked)
        save_button = Gtk.Button(label="save")
        save_button.connect("clicked", self.on_save_button_clicked)

        

        # Envelope input area
        envelope_widget = EnvelopeWidget(self.synth, env_ax, output_env_canvas)
        

        # edge box
        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation.VERTICAL)
        box.pack_start(play_button, True, True, 0)
        box.pack_start(save_button, True, True, 0)
        box.pack_start(chain_stack_switcher, True, True, 0)
        
        # figure frame
        figure_grid = Gtk.Grid()
        figure_grid.attach(self.output_canvas, 0, 0, 2, 4)
        figure_grid.attach(self.chain_plot_stack, 2, 0, 2, 2)
        figure_grid.attach(output_env_canvas, 2, 2, 2, 2)
        
        
        # lay everything out in a grid
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        grid.attach(box, 0, 0, 1, 3)
        grid.attach(Gtk.Separator(), 1, 0, 1, 3)
        grid.attach(Gtk.Separator(), 1, 1, 3, 1)
        chain_stack_frame = Gtk.Frame()
        chain_stack_frame.add(chain_stack)
        grid.attach(chain_stack_frame, 2, 0, 1, 1)
        envelope_widget_frame = Gtk.Frame()
        envelope_widget_frame.add(envelope_widget)
        grid.attach(envelope_widget_frame, 3, 0, 1, 1)
        grid.attach(figure_grid, 2, 2, 2, 1)
        
        self.add(grid)
        self.set_resizable(False)

    def switch_chain_plot(self, chain_stack: Gtk.Stack, gparamstring: str) -> None:
        """ Sets the visible chain plot to corresponding to the chain stack
        selected with the chain stack switcher.
        """
        page_name = chain_stack.get_visible_child_name()
        self.chain_plot_stack.set_visible_child_name(page_name)
        
    def _read_patch_from_file(self) -> dict:
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
        """ updates the output plot. """
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
