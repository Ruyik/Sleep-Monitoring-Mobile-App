import os
import threading
from datetime import datetime, timedelta

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.screenmanager import SlideTransition, Screen
from kivy.properties import NumericProperty, ListProperty, StringProperty
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.config import Config
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import get_color_from_hex
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.logger import Logger

# Set dimensions to a common mobile resolution (375x667 pixels)
Config.set('graphics', 'width', '375')
Config.set('graphics', 'height', '667')

# Prevent the user from resizing the window during the demo
Config.set('graphics', 'resizable', '0')

# Ensure the wm_pen fix is still applied
Config.set('input', 'wm_pen', '')

# Apply settings (optional, but good practice)
Config.write()

# --- CONFIGURATION (Must be executed first) ---
Config.set('input', 'wm_pen', '')
Window.size = (375, 667)
# ----------------------------------------------

# IMPORT BACKEND SERVICES
from backend.mqtt_client import DashboardClient
from backend.scheduler import SleepScheduler
from backend.database import Database
from backend.auth_service import AuthService
from backend.bot_screen import BotScreen
from backend.pet_service import PetService

MAX_DEVIATION = 180


# =========================================================
# --- ALL CUSTOM CLASS DEFINITIONS ---
# =========================================================

class IntroScreen(Screen): pass


class LoginScreen(Screen): pass


class RegisterScreen(Screen): pass


class ForgotPasswordScreen(Screen): pass


class HomeScreen(Screen): pass


class SleepScheduleScreen(Screen): pass


class CountdownScreen(Screen): pass


class ExtendScreen(Screen): pass


class ConsistencyScreen(Screen):
    # This method is called by the BarChartColumn in KV
    def get_score_color(self, score):
        """Delegates the color calculation logic from ScoreSegment."""
        # This is a safe way to reuse the logic without changing the segment's structure

        if score == 0:
            return 0.7, 0.7, 0.7, 1
        elif score >= 95:
            return get_color_from_hex('#4CAF50')
        elif score >= 85:
            return get_color_from_hex('#FFC107')
        else:
            return get_color_from_hex('#F44336')

class DashboardScreen(Screen): pass


class ScoreSegmentLabel(Label): pass  # Unused, but kept for context

class PetStatusScreen(Screen):
    def on_enter(self):
        """Automatically updates pet status when the user switches to this screen."""
        # This tells the main app to run the update logic whenever this screen appears
        app = App.get_running_app()
        app.update_pet_on_status_screen()

# --- Consistency Heat Bar Components ---

class ScoreSegment(BoxLayout):
    score = NumericProperty(100)

    # Hardcoded RGBA values to bypass get_color_from_hex dependency
    COLOR_GREEN = (0.29, 0.79, 0.31, 1.0) # #4CAF50
    COLOR_YELLOW = (1.0, 0.75, 0.0, 1.0) # #FFC107
    COLOR_RED = (0.95, 0.26, 0.21, 1.0) # #F44336
    COLOR_GRAY = (0.7, 0.7, 0.7, 1.0)   # Placeholder

    def get_color(self):
        """Maps the score value to a color tuple based on tiers (using hardcoded RGBA)."""

        if self.score == 0:
            return self.COLOR_GRAY

        if self.score >= 95:
            return self.COLOR_GREEN
        elif self.score >= 85:
            return self.COLOR_YELLOW
        else:
            return self.COLOR_RED

class ConsistencyHeatBar(BoxLayout):
    # This class was missing its Python definition
    scores = ListProperty([])
    # The on_scores method runs in KV, using this property

class BarChartColumn(BoxLayout):
    score = NumericProperty(0)
    date_label = StringProperty("")

# =========================================================
# --- WIDGET REGISTRATION (CRITICAL FIX FOR NameError) ---
# This ensures all custom classes are known to the Kivy Factory.
# =========================================================

Factory.register('ScoreSegment', cls=ScoreSegment)
Factory.register('ConsistencyHeatBar', cls=ConsistencyHeatBar)
Factory.register('BarChartColumn', cls=BarChartColumn)
Factory.register('IntroScreen', cls=IntroScreen)
Factory.register('LoginScreen', cls=LoginScreen)
Factory.register('RegisterScreen', cls=RegisterScreen)
Factory.register('ForgotPasswordScreen', cls=ForgotPasswordScreen)
Factory.register('HomeScreen', cls=HomeScreen)
Factory.register('SleepScheduleScreen', cls=SleepScheduleScreen)
Factory.register('CountdownScreen', cls=CountdownScreen)
Factory.register('ExtendScreen', cls=ExtendScreen)
Factory.register('ConsistencyScreen', cls=ConsistencyScreen)
Factory.register('DashboardScreen', cls=DashboardScreen)
Factory.register('BotScreen', cls=BotScreen)
Factory.register('PetStatusScreen', cls=PetStatusScreen)


# =========================================================
# --- MAIN APPLICATION LOGIC ---
# =========================================================

class SleepApp(App):
    target_sleep_time = None
    countdown_event = None
    auth_service = AuthService()

    # Properties for ExtendScreen picker (Used for state management)
    extend_hours = NumericProperty(0)
    extend_minutes = NumericProperty(0)
    MAX_EXTENSION_MINUTES = 180  # 3 hours

    def restart_bot(self):
        """Resets the bot conversation to the beginning."""
        bot_screen = self.root.get_screen('bot')
        if hasattr(bot_screen, 'reset_chat'):
            bot_screen.reset_chat()
        self.switch('bot')

    def build(self):

        # 1. HIDE WINDOW IMMEDIATELY to prevent flash
        Window.hide()

        self.db = Database()
        self.pet_service = PetService()
        self.dashboard_client = DashboardClient(self)
        self.scheduler = SleepScheduler(self, self.db)

        # 2. LOAD STYLES AND MAIN KV (After classes are registered)
        Builder.load_file("UI/styles.kv")
        self.root = Builder.load_file("UI/main.kv")

        # --- CRITICAL FIX START: Explicitly add ALL screens ---
        screens_to_add = [
            'IntroScreen', 'LoginScreen', 'RegisterScreen', 'ForgotPasswordScreen',
            'HomeScreen', 'SleepScheduleScreen', 'CountdownScreen', 'ExtendScreen',
            'ConsistencyScreen', 'DashboardScreen', 'BotScreen', 'PetStatusScreen',

        ]

        for screen_name in screens_to_add:
            try:
                screen_instance = Factory.get(screen_name)()
                self.root.add_widget(screen_instance)
                print(f"Added Screen: {screen_name}")
            except Exception as e:
                print(f"CRITICAL ERROR: Failed to instantiate {screen_name} from KV: {e}")
        # --- CRITICAL FIX END ---

        self.root.transition = SlideTransition()

        # 3. Schedule the setting of the initial screen (intro) and show the window
        Clock.schedule_once(self.show_intro_and_window, 0)
        Clock.schedule_once(lambda dt: self.dashboard_client.connect(), 1)

        return self.root

    def show_intro_and_window(self, dt):
        """Switches to the first screen and reveals the window."""
        self.switch('intro')  # This now correctly calls the switch method below
        Window.show()

    # -----------------------
    # NAVIGATION METHODS
    # -----------------------
    def switch(self, screen, direction='left'):
        """Sets the screen manager's current screen."""
        # FIX: The missing switch method is placed here
        self.root.transition.direction = direction
        self.root.current = screen

    def go_back(self):
        """
        Checks if a countdown is active. If yes, return to countdown.
        Otherwise, return to home.
        """
        now = datetime.now()
        if self.target_sleep_time and self.target_sleep_time > now:
            self.switch("countdown", direction='right')
        else:
            self.switch("home", direction='right')

    # ... (rest of methods) ...

    def on_stop(self):
        """Disconnect MQTT clients when the application closes."""
        self.dashboard_client.disconnect()

    # --- ASYNCHRONOUS AUTHENTICATION HANDLERS ---
    def async_call(self, func, *args, success_callback, error_callback=None):
        """Wrapper for long-running blocking tasks to prevent UI freeze."""

        def thread_target():
            try:
                result = func(*args)
                Clock.schedule_once(lambda dt: success_callback(result), 0)
            except Exception as e:
                if error_callback:
                    Clock.schedule_once(lambda dt: error_callback(str(e)), 0)
                else:
                    print(f"Async call failed: {e}")

        threading.Thread(target=thread_target).start()

    def handle_login(self, username, password):
        screen = self.root.get_screen('login')
        screen.ids.status_lbl.text = "Logging in..."
        self.async_call(
            self.auth_service.login_user,
            username, password,
            success_callback=self.login_success,
            error_callback=lambda msg: self.set_status(screen, f"Login Error: {msg}")
        )

    def handle_register(self, username, email, password):
        screen = self.root.get_screen('register')
        screen.ids.status_lbl.text = "Registering user..."
        self.async_call(
            self.auth_service.register_user,
            username, email, password,
            success_callback=self.register_success,
            error_callback=lambda msg: self.set_status(screen, f"Registration Error: {msg}")
        )

    def handle_forgot_password(self, email):
        screen = self.root.get_screen('forgot_password')
        screen.ids.status_lbl.text = "Sending reset email..."
        self.async_call(
            self.auth_service.send_reset_email,
            email,
            success_callback=self.reset_email_success,
            error_callback=lambda msg: self.set_status(screen, f"Email Error: {msg}")
        )

    # --- AUTHENTICATION CALLBACKS (omitted for brevity) ---
    def login_success(self, result):
        screen = self.root.get_screen('login')

        if result.startswith("✅"):
            # Use 'username_input' to match your KV file
            username = screen.ids.username_input.text.strip().lower()

            if not username:
                username = "unknown_user"

            # Initialize the private database for this user
            self.db = Database(user_id=username)

            self.update_consistency()
            self.set_status(screen, result)
            self.switch("home")
        else:
            self.set_status(screen, result)

    def register_success(self, result):
        screen = self.root.get_screen('register')
        self.set_status(screen, result)
        if result.startswith("✅"):
            Clock.schedule_once(lambda dt: self.switch("login"), 1.5)

    def reset_email_success(self, result):
        screen = self.root.get_screen('forgot_password')
        self.set_status(screen, result)
        if result.startswith("Password reset"):
            Clock.schedule_once(lambda dt: self.switch("login"), 2)

    def set_status(self, screen, text):
        if hasattr(screen.ids, 'status_lbl'):
            screen.ids.status_lbl.text = text


    def save_sleep_time(self, time_str):
        print("Saved sleep time:", time_str)

        # 1. Call the combined method: Calculate, save to history, and reset counter.
        try:
            # This single call now handles: calculating score, saving it permanently, and resetting the counter.
            self.db.save_current_period_score()
            print("[DB] Score saved and deviation counter reset for new period.")
        except Exception as e:
            # If this fails, the error will be printed, but the schedule will still be saved.
            print(f"DB save_current_period_score failed: {e}")

            # 2. Save the new schedule record and update the UI.
        self.db.save_schedule(time_str)
        self.update_consistency()
        self.start_countdown(time_str)
        self.switch("countdown")
    def start_countdown(self, time_str):
        try:
            user_time = datetime.strptime(time_str, "%I:%M %p")
        except Exception as e:
            print("Time parse error:", e)
            return

        now = datetime.now()
        self.target_sleep_time = now.replace(
            hour=user_time.hour,
            minute=user_time.minute,
            second=0,
            microsecond=0
        )
        if self.target_sleep_time <= now:
            self.target_sleep_time += timedelta(days=1)

        print("Target sleep datetime:", self.target_sleep_time)

        if self.countdown_event:
            try:
                self.countdown_event.cancel()
            except Exception:
                pass
            self.countdown_event = None
        self.countdown_event = Clock.schedule_interval(self.update_countdown, 1)
        self.update_countdown(0)

    def update_countdown(self, dt):
        if not self.target_sleep_time:
            return
        now = datetime.now()
        remaining = self.target_sleep_time - now
        if remaining.total_seconds() <= 0:
            self.update_countdown_label("00:00:00")
            self.sleep_time_reached()
            if self.countdown_event:
                try:
                    self.countdown_event.cancel()
                except Exception:
                    pass
            return False

        total_sec = int(remaining.total_seconds())
        h = total_sec // 3600
        m = (total_sec % 3600) // 60
        s = total_sec % 60
        self.update_countdown_label(f"{h:02d}:{m:02d}:{s:02d}")

    def update_countdown_label(self, text):
        try:
            screen = self.root.get_screen("countdown")
            screen.ids.countdown_label.text = text
        except Exception:
            pass

    def sleep_time_reached(self):
        print("Sleep Time Reached!")
        self.dashboard_client.publish_turn_off()
        try:
            screen = self.root.get_screen("countdown")
            screen.ids.status_msg.text = "Light turned off. Ready for sleep."
            screen.ids.countdown_label.text = ""
        except Exception:
            pass
        try:
            self.db.log_event("sleep_time_reached")
            print("[DB] Event logged: sleep_time_reached")
        except Exception as e:
            print("DB error:", e)

    def extend_time(self, minutes):
        mins = int(minutes)
        if mins < 0 or mins > self.MAX_EXTENSION_MINUTES: raise ValueError
        try:
            self.db.save_extension(mins)
        except Exception as e:
            print("DB save_extension failed:", e)

        if self.target_sleep_time:
            self.target_sleep_time += timedelta(minutes=mins)
            self.update_countdown(0)
            if not self.countdown_event:
                self.countdown_event = Clock.schedule_interval(self.update_countdown, 1)
        else:
            self.target_sleep_time = datetime.now() + timedelta(minutes=mins)
            if self.countdown_event:
                try:
                    self.countdown_event.cancel()
                except Exception:
                    pass
            self.countdown_event = Clock.schedule_interval(self.update_countdown, 1)
            self.update_countdown(0)

        self.update_consistency()
        self.extend_hours = 0
        self.extend_minutes = 0
        self.reset_extend_picker()
        self.switch("countdown")

    def on_start(self):
        Clock.schedule_once(self.update_consistency, 0.5)

    # In main.py (Inside SleepApp class)
    # In main.py
    # In main.py (Inside SleepApp class)
    def update_consistency(self, *args):
        try:
            # 1. Check current extensions
            ext_list = self.db.get_all_extensions()
            total_ext = sum(ext_list) if ext_list else 0
            current_score = self.db._calculate_score_from_minutes(total_ext)

            # 2. Get history
            historical_data = self.db.get_recent_consistency_scores(days=7)

            if not historical_data and total_ext == 0:
                # NEW USER LOGIC: If no history and no current extension, start at 0
                current_score = 0
            else:
                # REGULAR LOGIC: 0 deviation means 100%
                current_score = self.db._calculate_score_from_minutes(total_ext)

            today_label = datetime.now().strftime("%b %d")
            chart_data_updated = False
            final_chart_data = []

            for date_label, score in historical_data:
                if date_label == today_label:
                    final_chart_data.append((current_score, date_label))
                    chart_data_updated = True
                else:
                    final_chart_data.append((float(score), date_label))

            if not chart_data_updated:
                final_chart_data.append((current_score, today_label))

            # Update Labels
            score_text = f"Your Sleep Consistency Level\n\n[size=100]{current_score}%[/size]"
            screen = self.root.get_screen("consistency")
            if hasattr(screen.ids, 'score_label'):
                screen.ids.score_label.text = score_text

            # Update Chart
            if hasattr(screen.ids, 'score_bar'):
                screen.ids.score_bar.scores = []
                screen.ids.score_bar.scores = final_chart_data

            # Update Pet (Syncing with the new PetStatusScreen IDs)
            try:
                img_path, status_text, text_color = self.pet_service.calculate_pet_state(current_score)
                pet_screen = self.root.get_screen("pet_status")
                pet_screen.ids.detail_pet_image.source = img_path
                pet_screen.ids.detail_pet_status.text = f"Status: {status_text}"
                pet_screen.ids.detail_pet_status.color = text_color
            except:
                pass

        except Exception as e:
            Logger.error(f"update_consistency failed: {e}")

    def update_pet_on_status_screen(self):
        """Specifically updates the IDs on the PetStatusScreen with New User logic."""
        try:
            # 1. Get Live Data
            ext_list = self.db.get_all_extensions()
            total_ext_minutes = sum(ext_list) if ext_list else 0

            # 2. NEW USER LOGIC: Check if history exists
            # This mirrors the fix in your update_consistency function
            historical_data = self.db.get_recent_consistency_scores(days=7)

            if not historical_data and total_ext_minutes == 0:
                current_score = 0.0  # Force 0% for new users
            else:
                current_score = self.db._calculate_score_from_minutes(total_ext_minutes)

            # 3. Target the PetStatusScreen
            screen = self.root.get_screen("pet_status")

            # 4. Get the correct pet state
            img_path, status_text, text_color = self.pet_service.calculate_pet_state(current_score)

            # 5. Update the UI elements
            if hasattr(screen.ids, 'detail_pet_image'):
                screen.ids.detail_pet_image.source = img_path

            if hasattr(screen.ids, 'detail_pet_status'):
                screen.ids.detail_pet_status.text = f"Status: {status_text}"
                screen.ids.detail_pet_status.color = text_color

            Logger.info(f"PetStatusScreen: UI updated successfully for score {current_score}%")

        except Exception as e:
            Logger.error(f"PetStatusScreen update failed: {e}")

    def increment_hour(self):
        s = self.root.get_screen("schedule")
        h = int(s.ids.hour_label.text)
        s.ids.hour_label.text = "1" if h == 12 else str(h + 1)

    def decrement_hour(self):
        s = self.root.get_screen("schedule")
        h = int(s.ids.hour_label.text)
        s.ids.hour_label.text = "12" if h == 1 else str(h - 1)

    def increment_minute(self):
        s = self.root.get_screen("schedule")
        m = int(s.ids.minute_label.text)
        m = 0 if m == 59 else m + 1
        s.ids.minute_label.text = f"{m:02d}"

    def decrement_minute(self):
        s = self.root.get_screen("schedule")
        m = int(s.ids.minute_label.text)
        m = 59 if m == 0 else m - 1
        s.ids.minute_label.text = f"{m:02d}"

    def toggle_ampm(self):
        s = self.root.get_screen("schedule")
        s.ids.ampm_label.text = "PM" if s.ids.ampm_label.text == "AM" else "AM"

    def get_timepicker_value(self):
        s = self.root.get_screen("schedule")
        return f"{int(s.ids.hour_label.text):02d}:{int(s.ids.minute_label.text):02d} {s.ids.ampm_label.text}"

    def reset_extend_picker(self):
        """Resets the KV labels after confirmation."""
        s = self.root.get_screen("extend")
        s.ids.ext_hour.text = "0"
        s.ids.ext_minute.text = "00"

    def _get_current_total_minutes(self):
        """Calculates total selected minutes from KV labels."""
        s = self.root.get_screen("extend")
        h = int(s.ids.ext_hour.text)
        m = int(s.ids.ext_minute.text)
        return h * 60 + m

    def increment_extend_hour(self):
        s = self.root.get_screen("extend")
        h = int(s.ids.ext_hour.text)
        current_minutes = self._get_current_total_minutes()

        if current_minutes + 60 <= self.MAX_EXTENSION_MINUTES:
            s.ids.ext_hour.text = str(h + 1)

    def decrement_extend_hour(self):
        s = self.root.get_screen("extend")
        h = int(s.ids.ext_hour.text)
        if h > 0:
            s.ids.ext_hour.text = str(h - 1)

    def increment_extend_minute(self):
        s = self.root.get_screen("extend")
        h = int(s.ids.ext_hour.text)
        m = int(s.ids.ext_minute.text)
        current_minutes = h * 60 + m

        if current_minutes + 1 <= self.MAX_EXTENSION_MINUTES:
            m += 1
            if m == 60:
                h += 1
                m = 0
                s.ids.ext_hour.text = str(h)
            s.ids.ext_minute.text = f"{m:02d}"

        elif current_minutes == self.MAX_EXTENSION_MINUTES:
            pass

    def decrement_extend_minute(self):
        s = self.root.get_screen("extend")
        h = int(s.ids.ext_hour.text)
        m = int(s.ids.ext_minute.text)
        current_minutes = h * 60 + m

        if current_minutes > 0:
            m -= 1
            if m < 0:
                h -= 1
                m = 59
                s.ids.ext_hour.text = str(h)
            s.ids.ext_minute.text = f"{m:02d}"

        if h < 0: h = 0
        if m < 0: m = 0

        s.ids.ext_hour.text = str(h)
        s.ids.ext_minute.text = f"{m:02d}"

    def confirm_extension(self):
        screen = self.root.get_screen("extend")
        h = int(screen.ids.ext_hour.text)
        m = int(screen.ids.ext_minute.text)

        total_minutes = h * 60 + m
        if total_minutes > self.MAX_EXTENSION_MINUTES:
            total_minutes = self.MAX_EXTENSION_MINUTES

        print(f"Extension confirmed: {total_minutes} minutes")
        self.extend_time(total_minutes)


if __name__ == "__main__":
    SleepApp().run()