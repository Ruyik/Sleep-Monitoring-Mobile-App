from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, NumericProperty
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.uix.button import Button

Factory.register('OptionButton', cls=Button)
class ChatBubble(BoxLayout):
    message = StringProperty("")
    image_path = StringProperty("")
    is_bot = NumericProperty(1)
    avatar = StringProperty("UI/images/bot_avatar.png")

class BotScreen(Screen):
    # Expanded tree logic data mapping
    TREE_LOGIC = {
        # 1. ANXIETY PATH
        "Racing Thoughts/Anxiety": {
            "question": "I understand. What kind of anxiety is keeping you awake?",
            "options": ["Academic Pressure", "Relationship Issues", "Work Stress"]
        },
        "Academic Pressure": {
            "msg": "Schedule a 15-min 'Review Sprint' for 7 AM. Closing your books now allows your brain to process data during REM sleep.",
            "img": "UI/images/academic_sol.png"
        },
        "Relationship Issues": {
            "msg": "Try 'Externalizing': Write your feelings on paper. This signals to your brain that the information is 'stored' and safe to stop cycling.",
            "img": "UI/images/relation_sol.png"
        },
        "Work Stress": {
            "msg": "Write down the TOP 3 tasks for tomorrow. This 'unloads' your prefrontal cortex so it can enter sleep mode.",
            "img": "UI/images/work_stress_sol.png"
        },

        # 2. DIGITAL PATH
        "Digital Addiction": {
            "question": "Screens mimic daylight. What are you currently using?",
            "options": ["Social Media Binging", "Mobile Gaming", "Streaming Videos"]
        },
        "Social Media Binging": {
            "msg": "Enable 'Grayscale Mode' to make apps less stimulating. The lack of color reduces dopamine hits.",
            "img": "UI/images/social_media_sol.png"
        },
        "Mobile Gaming": {
            "msg": "Gaming keeps your brain in 'Active-Beta' waves. Switch to a boring podcast or white noise to trigger 'Alpha' waves.",
            "img": "UI/images/gaming_sol.png"
        },
        "Streaming Videos": {
            "msg": "Use a Blue Light Filter and move the device 2 meters away. Physical distance prevents the urge to 'just one more'.",
            "img": "UI/images/video_binge_sol.png"
        },

        # 3. ENVIRONMENT PATH
        "Environmental Issues": {
            "question": "Your surroundings affect deep sleep. What is the main problem?",
            "options": ["Room is Too Hot", "Sudden Noises", "Too Much Light"]
        },
        "Room is Too Hot": {
            "msg": "The body needs to drop 1°C to fall asleep. Use a fan or thin cotton sheets to help heat escape.",
            "img": "UI/images/temp_sol.png"
        },
        "Sudden Noises": {
            "msg": "Sudden sounds trigger 'Startle Response'. Use a White Noise machine to mask background sounds.",
            "img": "UI/images/noise_sol.png"
        },
        "Too Much Light": {
            "msg": "Even dim light stops Melatonin production. Use an eye mask or blackout curtains for total darkness.",
            "img": "UI/images/light_sol.png"
        },

        # 4. CAFFEINE PATH
        "Late Caffeine/Food": {
            "question": "What did you consume late in the evening?",
            "options": ["Coffee/Espresso", "Energy Drinks", "Sugary Snacks/Tea"]
        },
        "Coffee/Espresso": {
            "msg": "Caffeine has a 6-hour half-life. Drink 500ml of water to help your kidneys process it faster.",
            "img": "UI/images/coffee_timing_sol.png"
        },
        "Energy Drinks": {
            "msg": "These contain Taurine which keeps the heart rate high. Try a 5-minute slow-stretching routine to lower your pulse.",
            "img": "UI/images/energy_drink_sol.png"
        },
        "Sugary Snacks/Tea": {
            "msg": "Sugar spikes cause 'Alertness Waves'. Drink warm milk; it contains Tryptophan which counteracts the sugar rush.",
            "img": "UI/images/tea_sol.png"
        },

        # 5. PROCRASTINATION PATH
        "General Procrastination": {
            "question": "Why do you feel the urge to stay up longer?",
            "options": ["Fear of Tomorrow", "Feeling Productive Now", "Perfectionism"]
        },
        "Fear of Tomorrow": {
            "msg": "This is 'Revenge Bedtime Procrastination'. Claim 10 mins of 'Me Time' now with a book (no screens) to feel in control.",
            "img": "UI/images/planning_sol.png"
        },
        "Feeling Productive Now": {
            "msg": "Midnight productivity is often a 'False Second Wind'. Stop now; 1 hour of sleep is worth 3 hours of tired work.",
            "img": "UI/images/fear_failure_sol.png"
        },
        "Perfectionism": {
            "msg": "Accept that 'Done is better than Perfect'. Set a strict 'Shut Down' ritual to break the cycle of endless checking.",
            "img": "UI/images/perfectionism_sol.png"
        }
    }

    def on_enter(self):
        self.reset_chat()

    def reset_chat(self):
        self.ids.chat_history.clear_widgets()
        self.add_message("Hi, I am your sleeping assistant. What's preventing you from sleeping?", is_bot=1)
        self.show_options(["Racing Thoughts/Anxiety", "Digital Addiction", "Environmental Issues", "Late Caffeine/Food", "General Procrastination"])

    def add_message(self, text, is_bot=1, img=""):
        bubble = ChatBubble(message=text, is_bot=is_bot, image_path=img)
        self.ids.chat_history.add_widget(bubble)
        Clock.schedule_once(lambda dt: setattr(self.ids.chat_scroll, 'scroll_y', 0), 0.1)

    def show_options(self, options):
        self.ids.options_layout.clear_widgets()
        for opt in options:
            btn = Factory.OptionButton(
                text=opt,
                size_hint_y=None,
                height='48dp'
            )
            btn.bind(on_release=lambda x: self.handle_selection(x.text))
            self.ids.options_layout.add_widget(btn)

    def handle_selection(self, choice):
        self.add_message(choice, is_bot=0)
        self.ids.options_layout.clear_widgets()
        Clock.schedule_once(lambda dt: self.process_logic(choice), 0.6)

    def process_logic(self, choice):
        if choice in self.TREE_LOGIC:
            node = self.TREE_LOGIC[choice]
            if "question" in node:
                self.add_message(node["question"])
                self.show_options(node["options"])
            else:
                self.add_message(f"Customized Solution: {node['msg']}", img=node['img'])
                self.show_options(["Satisfied (Yes)", "Try another reason (No)"])
        elif choice == "Satisfied (Yes)":
            self.add_message("Excellent. I hope this helps you rest better. Goodnight!")
        elif choice == "Try another reason (No)":
            self.reset_chat()