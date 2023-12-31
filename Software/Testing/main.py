from setup import (
    neopixels,
    enc_buttons,
    display,
    encoder_1,
    midi_serial,
    midi_usb,
    keys,
)
from os import listdir
import displayio
import terminalio
from adafruit_display_text import label
import time
from supervisor import ticks_ms
import board
import audiobusio
import audiocore
import audiomixer
import usb_hid
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_midi.control_change import ControlChange
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.animation.rainbowchase import RainbowChase
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
from adafruit_led_animation.animation.rainbowsparkle import RainbowSparkle
from adafruit_led_animation.animation.sparklepulse import SparklePulse
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode


# Setup audio
audio = audiobusio.I2SOut(board.GP0, board.GP1, board.GP2)
num_voices = 9
mixer = audiomixer.Mixer(
    voice_count=num_voices,
    sample_rate=16000,
    channel_count=1,
    bits_per_sample=16,
    samples_signed=True,
)
clk_src = ""


# Function to scroll through a list of menu items and return a selection on encoder press
def menu_select(last_position, menu_items):
    # Force last_position to not equal encoder_1.position and be % = 0
    last_position = -len(menu_items)
    encoder_1.position = 0
    item_selected = False
    while item_selected is False:
        current_position = encoder_1.position

        # Generate a valid index from the position
        if current_position != last_position:
            index = current_position % len(menu_items)
            # Display item
            pretty_name = menu_items[index]["pretty"]
            text = str.format("{}: {}", index, pretty_name)
            text_area = label.Label(terminalio.FONT, text=text, x=2, y=15)
            display.show(text_area)
            last_position = current_position

        # Select item
        enc_buttons_event = enc_buttons.events.get()
        if enc_buttons_event and enc_buttons_event.pressed:
            index = current_position % len(menu_items)
            return menu_items[index]["name"]


# Function to program sequence values, should be used after a keypress
# On key release toggle state
# On key held and encoder turned, value changed
def sequence_selector(value, min_val, max_val, increment, key_val):
    selection = True
    vel_change = False
    encoder_pos = encoder_1.position
    # Display current value
    while selection:
        text = f"Step {key_val}: {value[key_val][1]:.2f}"
        text_area = label.Label(terminalio.FONT, text=text, x=2, y=5)
        display.show(text_area)
        key_event = keys.events.get()

        # Modify value on encoder input
        if encoder_pos is not encoder_1.position:
            if encoder_1.position < encoder_pos:
                if value[key_val][1] > min_val + increment:
                    value[key_val][1] = value[key_val][1] - increment
                else:
                    value[key_val][1] = min_val

            else:
                if value[key_val][1] < max_val - increment:
                    value[key_val][1] = value[key_val][1] + increment
                else:
                    value[key_val][1] = max_val
            encoder_pos = encoder_1.position
            vel_change = True

        # Exit selection menu if key released
        if key_event and key_event.released:
            if key_event.key_number == key_val:
                if not vel_change:
                    value[key_val][0] = not value[key_val][0]
                selection = False


# File sequencer class
# Sets up a sequence track to play a .wav file sample at regular intervals
# 8 step sequence tells whether to play
class file_sequence:
    def __init__(self):
        self.fname = ""
        self.sequence = [
            [False, 0.5],
            [True, 0.5],
            [True, 0.5],
            [True, 0.5],
            [True, 0.5],
            [True, 0.5],
            [True, 0.5],
            [True, 0.5],
        ]

    # Set and store a sequence with True/False indicating steps to play on and int being a velocity value between 0-1
    def set_sequence(self):
        # Enter sequence mode, set with keys, exit with encoder
        key_input = [
            [False, 0],
            [False, 0],
            [True, 0.5],
            [False, 0],
            [False, 0],
            [True, 0.5],
            [False, 0],
            [True, 0.5],
        ]
        self.sequence = key_input

    def show_sequence(self):
        for index, item in enumerate(self.sequence):
            if item[0]:
                neopixels[index] = (0, 0, 255)
                neopixels.show()
            elif item[0] is False:
                neopixels[index] = (255, 0, 0)
                neopixels.show()


class run_sequencer:
    def __init__(self):
        self.clk_src = "int"
        self.bpm = 120
        self.active_sequences = []
        self.sequence_step = 0
        self.wav_files = []
        self.loaded_wavs = []
        self.step = 0
        self.play_music = False

    # Add sequences to the active set
    def add_sequence(self, new_sequence):
        self.active_sequences.append(new_sequence)

    # Set BPM (needs integration with input, required)
    def set_bpm(self):
        # Display bpm on screen, select with enc knob/button
        screen_input = 120
        self.bpm = screen_input

    # Write sequence data to file to reload after power on/off (future)
    def save_sequence(self):
        pass

    # Load sequence from file to reload after power on/off (future)
    def load_sequence(self):
        pass

    # Select where clock is coming from (not critical, but high priority nice-to-have)
    def set_clk_src(self):
        # clk_options = ["ext, midi, int"]
        # Display clk_options on screen, scroll/select
        # Ext takes signal from sync in, midi syncs to midi input, int is
        # internally clocked
        if clk_src == "ext":
            print("need to implement")
        elif clk_src == "midi":
            print("need to implement")
        elif clk_src == "int":
            pass

    def play_step(self):
        # Calculate step duration
        self.step_start = ticks_ms()
        self.step_end = self.step_start + self.step_length

        # Loop through active sequences and play indicated steps
        for index, item in enumerate(self.active_sequences):
            if item.sequence[self.step][0]:
                # Set volume based on input value
                mixer.voice[index].level = item.sequence[self.step][1]
                mixer.voice[index].play(self.loaded_wavs[index])

        # Cycle sequencer LED
        neopixels[self.step] = (0, 0, 255)
        neopixels.show()

        # Wait for beat duration and watch for stop
        while ticks_ms() < self.step_end:
            # Update to play/pause button for final hardware
            enc_buttons_event = enc_buttons.events.get()
            if enc_buttons_event and enc_buttons_event.pressed:
                for index, item in enumerate(self.active_sequences):
                    mixer.voice[index].stop
                audio.stop()

            # Stop output at end of step duration
            else:
                for index, item in enumerate(self.active_sequences):
                    mixer.voice[index].stop

        neopixels.fill((255, 0, 0))
        neopixels.show()

    # Update step
    def step_update(self):
        if self.step < 7:
            self.step += 1
        else:
            self.step = 0

    def play_sequence(self):
        # Main sequencer loop
        # Calculate step duration
        self.step_length = int(1000 // (self.bpm / 60))
        self.play_step()
        self.step_update()


# MIDI Functions
def send_note_on(note, octv):
    note = (note) + (12 * octv)
    midi_serial.send(NoteOn(note, 120))
    midi_usb.send(NoteOn(note, 120))


def send_note_off(note, octv):
    note = (note) + (12 * octv)
    midi_serial.send(NoteOff(note, 0))
    midi_usb.send(NoteOff(note, 120))


def send_cc(number, val):
    midi_serial.send(ControlChange(number, val))
    midi_usb.send(ControlChange(number, val))


def show_menu(menu, highlight, shift):
    """Shows the menu on the screen"""

    display_group = displayio.Group()
    # bring in the global variables

    # menu variables
    item = 1
    line = 1
    line_height = 10
    offset = 5
    total_lines = 3

    color_bitmap = displayio.Bitmap(display.width, line_height, 1)
    color_palette = displayio.Palette(1)
    color_palette[0] = 0xFFFFFF  # White

    # Shift the list of files so that it shows on the display
    short_list = []
    for index in range(shift, shift + total_lines):
        try:
            short_list.append(menu[index]["pretty"])
        except IndexError:
            print("show_menu: Bad Index")
    for item in short_list:
        if highlight == line:
            white_rectangle = displayio.TileGrid(
                color_bitmap,
                pixel_shader=color_palette,
                x=0,
                y=((line - 1) * line_height),
            )
            display_group.append(white_rectangle)
            text_arrow = ">"
            text_arrow = label.Label(
                terminalio.FONT,
                text=text_arrow,
                color=0x000000,
                x=0,
                y=((line - 1) * line_height) + offset,
            )
            display_group.append(text_arrow)
            text_item = label.Label(
                terminalio.FONT,
                text=item,
                color=0x000000,
                x=10,
                y=((line - 1) * line_height) + offset,
            )
            display_group.append(text_item)
        else:
            text_item = label.Label(
                terminalio.FONT,
                text=item,
                x=10,
                y=((line - 1) * line_height) + offset,
            )
            display_group.append(text_item)
        line += 1
    display.show(display_group)


class State(object):
    def __init__(self):
        pass

    @property
    def name(self):
        return ""

    def enter(self, machine):
        pass

    def exit(self, machine):
        pass

    def update(self, machine):
        # if switch.fell:
        #    machine.paused_state = machine.state.name
        #    machine.pause()
        #    return False
        return True


class StateMachine(object):
    def __init__(self):
        self.state = None
        self.states = {}
        self.last_enc1_pos = encoder_1.position
        self.paused_state = None
        self.ticks_ms = 0
        self.animation = None

    def add_state(self, state):
        self.states[state.name] = state

    def go_to_state(self, state_name):
        if self.state:
            self.state.exit(self)
        self.state = self.states[state_name]
        self.state.enter(self)

    def update(self):
        if self.state:
            self.state.update(self)
            if self.ticks_ms > 0:
                time.sleep(self.ticks_ms / 1000)

    # When pausing, don't exit the state
    def pause(self):
        self.state = self.states["paused"]
        self.state.enter(self)

    # When resuming, don't re-enter the state
    def resume_state(self, state_name):
        if self.state:
            self.state.exit(self)
        self.state = self.states[state_name]


class PausedState(State):
    @property
    def name(self):
        return "paused"

    def enter(self, machine):
        State.enter(self, machine)

    def exit(self, machine):
        State.exit(self, machine)

    def update(self, machine):
        enc_buttons_event = enc_buttons.events.get()
        if enc_buttons_event and enc_buttons_event.pressed:
            machine.resume_state(machine.paused_state)


class StartupState(State):
    color = (0, 0, 0)
    timer = 0
    stage = 0

    @property
    def name(self):
        return "startup"

    def enter(self, machine):
        neopixels.fill((0, 0, 0))
        State.enter(self, machine)

    def exit(self, machine):
        neopixels.fill((255, 0, 0))
        self.color = (0, 0, 0)
        self.timer = 0
        self.stage = 0
        State.exit(self, machine)

    def update(self, machine):
        self.timer = self.timer + 1
        if self.stage == 0:
            text = "       DCZia\n  Electric Sampler"
            if len(text) > self.timer:
                text = text[0 : self.timer]
            text_area = label.Label(terminalio.FONT, text=text, x=2, y=5)
            display.show(text_area)
            self.color = (self.timer, self.timer, 0)
            if self.timer > (len(text) * 1.5):
                self.timer = 0
                self.stage = 1
        elif self.stage == 1:
            text = "Fueled by Green Chile\n     and Solder"
            if len(text) > self.timer:
                text = text[0 : self.timer]
            text_area = label.Label(terminalio.FONT, text=text, x=2, y=10)
            display.show(text_area)
            if self.timer > (len(text) * 1.5):
                self.timer = 0
                self.stage = 2
        else:
            if self.timer < (255 * 8):
                color = (0, self.timer % 255, 0)
                neopixels[self.timer // 255] = color
                neopixels.show()
                self.timer = self.timer + 1  # make it faster
            else:
                time.sleep(0.1)
                machine.go_to_state("menu")
        # Skip to menu if encoder is pressed
        enc_buttons_event = enc_buttons.events.get()
        if enc_buttons_event and enc_buttons_event.pressed:
            machine.go_to_state("menu")


class MenuState(State):
    menu_items = [
        {
            "name": "flashy",
            "pretty": "Flashy",
        },
        {
            "name": "sequencer",
            "pretty": "Sequencer",
        },
        {
            "name": "sampler",
            "pretty": "Sampler",
        },
        {
            "name": "midi_controller",
            "pretty": "MIDI Controller",
        },
        {
            "name": "hid",
            "pretty": "USB HID Mode",
        },
        {
            "name": "startup",
            "pretty": "Startup State (test)",
        },
    ]

    @property
    def name(self):
        return "menu"

    def __init__(self):
        self.total_lines = 3
        self.list_length = len(self.menu_items)
        self.highlight = 1
        self.shift = 0

    def enter(self, machine):
        self.last_position = 0
        if machine.animation is None:
            machine.animation = Rainbow(neopixels, speed=0.1)
        show_menu(self.menu_items, self.highlight, self.shift)
        State.enter(self, machine)

    def exit(self, machine):
        encoder_1.position = 0
        State.exit(self, machine)

    def update(self, machine):
        # Code for moving through menu and selecting mode
        if machine.animation:
            machine.animation.animate()
        # Some code here to use an encoder to scroll through menu options, press to select one
        position = encoder_1.position
        list_length = len(self.menu_items)  # TODO: Doesn't change every frame

        if self.last_position != position:
            if position < self.last_position:
                if self.highlight > 1:
                    self.highlight -= 1
                else:
                    if self.shift > 0:
                        self.shift -= 1
            else:
                if self.highlight < self.total_lines:
                    self.highlight += 1
                else:
                    if self.shift + self.total_lines < list_length:
                        self.shift += 1
            show_menu(self.menu_items, self.highlight, self.shift)
        self.last_position = position

        enc_buttons_event = enc_buttons.events.get()
        if enc_buttons_event and enc_buttons_event.pressed:
            machine.go_to_state(
                self.menu_items[self.highlight - 1 + self.shift]["name"]
            )


class SequencerState(State):
    @property
    def name(self):
        return "sequencer"

    def enter(self, machine):
        State.enter(self, machine)

    def exit(self, machine):
        State.exit(self, machine)

    def update(self, machine):
        # Sequencer code
        text = "Sequencer"
        text_area = label.Label(terminalio.FONT, text=text, x=2, y=15)
        display.show(text_area)
        run_sequencer = True
        while run_sequencer is True:
            # send_note_on(1,4)
            # time.sleep(1.5)
            # send_note_off(1,4)
            # time.sleep(1.5)
            # send_note_on(5,4)
            # time.sleep(1.5)
            # send_note_off(5,4)
            # time.sleep(1.5)
            enc_buttons_event = enc_buttons.events.get()
            if enc_buttons_event and enc_buttons_event.pressed:
                run_sequencer = False
                machine.go_to_state("menu")


class SamplerState(State):
    seq_menu_items = [
        {
            "name": "add_sequence",
            "pretty": "Add Sequence",
        },
        {
            "name": "remove_sequence",
            "pretty": "Remove Sequence",
        },
        {
            "name": "edit_sequence",
            "pretty": "Edit Sequence",
        },
        {
            "name": "play_sequence",
            "pretty": "Play Sequence",
        },
        {
            "name": "exit",
            "pretty": "Exit",
        },
    ]

    @property
    def name(self):
        return "sampler"

    def __init__(self):
        self.total_lines = 3
        self.list_length = len(self.seq_menu_items)
        self.highlight = 1
        self.shift = 0

    def enter(self, machine):
        self.last_position = 0
        show_menu(self.seq_menu_items, self.highlight, self.shift)
        neopixels.fill((255, 0, 0))
        neopixels.show()
        State.enter(self, machine)

    def exit(self, machine):
        State.exit(self, machine)

    def select_wav(self):
        # Show valid files, select with encoder knob/button
        files = listdir("/samples/")
        wav_files = []
        for file in files:
            if file.endswith(".wav"):
                wav_files.append({"name": file, "pretty": file})
        selection = menu_select(encoder_1.position, wav_files)
        return selection

    def select_sequence(self, sequence_array):
        # Show valid sequences, select with encoder knob/button
        seq_select = []
        for index, seq in enumerate(sequence_array):
            seq_select.append({"name": index, "pretty": seq.fname})
        selection = menu_select(encoder_1.position, seq_select)
        return selection

    def update(self, machine):
        # Show selection menu
        # selection = menu_select(machine.last_enc1_pos, self.seq_menu_items)
        position = encoder_1.position
        list_length = len(self.seq_menu_items)  # TODO: Doesn't change every frame

        if self.last_position != position:
            if position < self.last_position:
                if self.highlight > 1:
                    self.highlight -= 1
                else:
                    if self.shift > 0:
                        self.shift -= 1
            else:
                if self.highlight < self.total_lines:
                    self.highlight += 1
                else:
                    if self.shift + self.total_lines < list_length:
                        self.shift += 1
            show_menu(self.seq_menu_items, self.highlight, self.shift)
        self.last_position = position

        enc_buttons_event = enc_buttons.events.get()
        if enc_buttons_event and enc_buttons_event.pressed:
            selection = self.seq_menu_items[self.highlight - 1 + self.shift]["name"]
            if selection == "add_sequence":
                # Display select file
                text = "Select File"
                text_area = label.Label(
                    terminalio.FONT, text=text, color=0xFFFF00, x=2, y=15
                )
                display.show(text_area)
                time.sleep(1)
                # Select file
                selected_file = self.select_wav()
                sequencer.add_sequence(file_sequence())

                # Create new sequence
                sequencer.active_sequences[-1].fname = str(f"/samples/{selected_file}")
                sequencer.active_sequences[-1].sequence = [
                    [False, 0.5],
                    [False, 0.5],
                    [False, 0.5],
                    [False, 0.5],
                    [False, 0.5],
                    [False, 0.5],
                    [False, 0.5],
                    [False, 0.5],
                ]
                # Display select file
                text = "Sequence Created"
                text_area = label.Label(terminalio.FONT, text=text, x=2, y=15)
                display.show(text_area)
                time.sleep(1)
                enc_buttons_event = enc_buttons.events.get()
                if enc_buttons_event and enc_buttons_event.pressed:
                    pass
            if selection == "remove_sequence":
                if len(sequencer.active_sequences) == 0:
                    text = "No Active Sequences"
                    text_area = label.Label(terminalio.FONT, text=text, x=2, y=15)
                    display.show(text_area)
                    time.sleep(0.5)
                else:
                    remove_seq = self.select_sequence(sequencer.active_sequences)
                    print(remove_seq)
                    del sequencer.active_sequences[remove_seq]

            if selection == "edit_sequence":
                # Check if sequences exist
                if len(sequencer.active_sequences) == 0:
                    text = "No Active Sequences"
                    text_area = label.Label(terminalio.FONT, text=text, x=2, y=15)
                    display.show(text_area)
                    time.sleep(0.5)
                else:
                    editing_sequence = True

                    # Select sequence
                    selected_sequence = self.select_sequence(
                        sequencer.active_sequences
                    )  # Modify to index based on selected
                    sequencer.active_sequences[selected_sequence].show_sequence()

                    # Display
                    text = f"Edit {sequencer.active_sequences[selected_sequence].fname}"
                    text_area = label.Label(terminalio.FONT, text=text, x=2, y=15)
                    display.show(text_area)

                    sequencer.active_sequences[selected_sequence].show_sequence()
                    neopixels.show()
                    machine.last_enc1_pos = encoder_1.position
                    while editing_sequence is True:
                        # Code to edit a sequence here
                        key_event = keys.events.get()
                        if key_event and key_event.pressed:
                            key = key_event.key_number
                            sequence_selector(
                                sequencer.active_sequences[selected_sequence].sequence,
                                0,
                                1,
                                0.05,
                                key,
                            )
                            sequencer.active_sequences[
                                selected_sequence
                            ].show_sequence()
                            neopixels.show()
                        # Update to play/pause button for final hardware
                        enc_buttons_event = enc_buttons.events.get()
                        if enc_buttons_event and enc_buttons_event.pressed:
                            editing_sequence = False
                        # Press encoder to exit
                        # Press play to start

            if selection == "play_sequence":
                machine.go_to_state("sampler_play")

            if selection == "exit":
                machine.go_to_state("menu")


class SamplerPlay(State):
    @property
    def name(self):
        return "sampler_play"

    def enter(self, machine):
        text = "Playing"
        text_area = label.Label(terminalio.FONT, text=text, x=2, y=15)
        display.show(text_area)
        neopixels.fill((255, 0, 0))
        neopixels.show()

        # Loop through active sequences and load wav files
        for item in sequencer.active_sequences:
            # Load wav files to play
            sequencer.wav_files.append(open(item.fname, "rb"))
            sequencer.loaded_wavs.append(audiocore.WaveFile(sequencer.wav_files[-1]))

        audio.play(mixer)
        State.enter(self, machine)

    def exit(self, machine):
        State.exit(self, machine)

    def update(self, machine):
        sequencer.play_sequence()
        if audio.playing is False:
            sequencer.step = 0
            sequencer.wav_files = []
            sequencer.loaded_wavs = []
            machine.go_to_state("sampler")


class MIDIState(State):
    @property
    def name(self):
        return "midi_controller"

    def enter(self, machine):
        text = "MIDI Controller"
        text_area = label.Label(terminalio.FONT, text=text, x=2, y=15)
        display.show(text_area)
        neopixels.fill((100, 100, 100))
        neopixels.show()
        State.enter(self, machine)

    def exit(self, machine):
        State.exit(self, machine)

    def update(self, machine):
        key_event = keys.events.get()
        while key_event:
            if key_event.pressed:
                key = key_event.key_number
                send_note_on(key, 4)
                neopixels[key] = (255, 0, 0)
            if key_event.released:
                key = key_event.key_number
                send_note_off(key, 4)
                neopixels[key] = (100, 100, 100)
            key_event = keys.events.get()

        neopixels.show()
        enc_buttons_event = enc_buttons.events.get()
        if enc_buttons_event and enc_buttons_event.pressed:
            machine.go_to_state("menu")


class FlashyState(State):
    menu_items = [
        {
            "function": "rainbow",
            "pretty": "Rainbow",
        },
        {
            "function": "rainbow_chase",
            "pretty": "Rainbow Chase",
        },
        {
            "function": "rainbow_comet",
            "pretty": "Rainbow Comet",
        },
        {
            "function": "rainbow_sparkle",
            "pretty": "Rainbow Sparkle",
        },
        {
            "function": "sparkle_pulse",
            "pretty": "Sparkle Pulse",
        },
    ]

    @property
    def name(self):
        return "flashy"

    def __init__(self):
        self.total_lines = 3
        self.list_length = len(self.menu_items)
        self.highlight = 1
        self.shift = 0

    def enter(self, machine):
        self.last_position = 0
        show_menu(self.menu_items, self.highlight, self.shift)
        State.enter(self, machine)

    def exit(self, machine):
        neopixels.fill((255, 0, 0))
        neopixels.show()
        encoder_1.position = 0
        State.exit(self, machine)

    def update(self, machine):
        position = encoder_1.position
        list_length = len(self.menu_items)  # TODO: Doesn't change every frame

        if self.last_position != position:
            if position < self.last_position:
                if self.highlight > 1:
                    self.highlight -= 1
                else:
                    if self.shift > 0:
                        self.shift -= 1
            else:
                if self.highlight < self.total_lines:
                    self.highlight += 1
                else:
                    if self.shift + self.total_lines < list_length:
                        self.shift += 1
            show_menu(self.menu_items, self.highlight, self.shift)
            selection = self.menu_items[self.highlight - 1 + self.shift]["function"]
            self.animation_selector(machine, selection)
        if machine.animation:
            machine.animation.animate()
        self.last_position = position
        enc_buttons_event = enc_buttons.events.get()
        if enc_buttons_event and enc_buttons_event.pressed:
            machine.go_to_state("menu")

    def animation_selector(self, machine, name):
        if name == "rainbow":
            machine.animation = Rainbow(neopixels, speed=0.1)
        elif name == "rainbow_chase":
            machine.animation = RainbowChase(neopixels, speed=0.1)
        elif name == "rainbow_comet":
            machine.animation = RainbowComet(neopixels, speed=0.1, tail_length=10)
        elif name == "rainbow_sparkle":
            machine.animation = RainbowSparkle(
                neopixels, speed=0.1, period=5, num_sparkles=None, step=1
            )
        elif name == "sparkle_pulse":
            machine.animation = SparklePulse(
                neopixels,
                speed=0.1,
                color=(0, 255, 0),
                period=5,
                max_intensity=1,
                min_intensity=0,
            )


class HIDState(State):
    keymap = [
        Keycode.KEYPAD_ONE,
        Keycode.KEYPAD_TWO,
        Keycode.KEYPAD_THREE,
        Keycode.KEYPAD_FOUR,
        Keycode.KEYPAD_FIVE,
        Keycode.KEYPAD_SIX,
        Keycode.KEYPAD_SEVEN,
        Keycode.KEYPAD_EIGHT,
    ]

    @property
    def name(self):
        return "hid"

    def __init__(self):
        try:
            self.kbd = Keyboard(usb_hid.devices)
            self.consumer_control = ConsumerControl(usb_hid.devices)
        except:
            # Dummy functions when we aren't plugged into a computer
            class fakekb:
                def press(self, foo):
                    print("No keyboard:", foo)

                def release(self, foo):
                    print("No keyboard:", foo)

                def send(self, foo):
                    print("No keyboard:", foo)

            self.kbd = fakekb()
            self.consumer_control = fakekb()

    def enter(self, machine):
        text = "HID Controller"
        text_area = label.Label(terminalio.FONT, text=text, x=2, y=15)
        display.show(text_area)
        neopixels.fill((100, 100, 100))
        neopixels.show()
        encoder_1.position = 0
        self.last_position = 0
        State.enter(self, machine)

    def exit(self, machine):
        encoder_1.position = 0
        State.exit(self, machine)

    def update(self, machine):
        cur_position = encoder_1.position
        if cur_position != self.last_position:
            if cur_position > self.last_position:
                self.consumer_control.send(ConsumerControlCode.VOLUME_INCREMENT)
            else:
                self.consumer_control.send(ConsumerControlCode.VOLUME_DECREMENT)
            self.last_position = cur_position
        #
        # Handle keyswitches
        #
        key_event = keys.events.get()
        while key_event:
            if key_event.pressed:
                self.kbd.press(self.keymap[key_event.key_number])
                neopixels[key_event.key_number] = (255, 0, 0)
            if key_event.released:
                self.kbd.release(self.keymap[key_event.key_number])
                neopixels[key_event.key_number] = (100, 100, 100)
            key_event = keys.events.get()
        neopixels.show()
        enc_buttons_event = enc_buttons.events.get()
        if enc_buttons_event and enc_buttons_event.pressed:
            neopixels.fill((255, 0, 0))
            neopixels.show()
            machine.go_to_state("menu")


machine = StateMachine()
machine.add_state(StartupState())
machine.add_state(MenuState())
machine.add_state(SequencerState())
machine.add_state(SamplerState())
machine.add_state(SamplerPlay())
machine.add_state(MIDIState())
machine.add_state(FlashyState())
machine.add_state(HIDState())
sequencer = run_sequencer()

machine.go_to_state("startup")

while True:
    machine.update()
