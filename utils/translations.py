"""Multilingual translation system for KisanSense.

Supports English (en), Hindi (hi), Tamil (ta), and Kannada (kn).
Callers retrieve strings via t(key, lang=None). When lang is omitted,
the language currently stored in st.session_state.lang is used, with an
automatic fallback to English if a key is not found in the selected locale.
"""

from __future__ import annotations

DEFAULT_LANG = "en"

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "hi": "हिन्दी (Hindi)",
    "ta": "தமிழ் (Tamil)",
    "kn": "ಕನ್ನಡ (Kannada)",
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # Navigation
        "nav_home": "Home",
        "nav_farm": "Farm",
        "nav_irrigation": "Irrigation",
        "nav_vision": "Vision",
        "nav_assistant": "Assistant",
        "nav_alerts": "Alerts",
        # Home page
        "home_tagline": "Smart farming, made simple.",
        "home_status_active": "Farm monitoring active",
        "home_empty_profile_prompt": "Set up your farm profile to personalize KisanSense.",
        "home_setup_profile_btn": "Set Up Profile",
        "home_farm_active_banner": "Active Farm Context",
        "home_alerts_title": "Important Alerts",
        "home_alert_water_needed": "Soil moisture is low. Irrigation is advised for your farm.",
        # Metric cards
        "card_soil_title": "Soil Moisture",
        "card_temp_title": "Temperature",
        "card_humidity_title": "Air Humidity",
        "card_irrigation_title": "Irrigation",
        "card_soil_desc": "Based on the latest reading from your farm's soil sensor.",
        "card_temp_desc": "Comfortable range for most crops is 15°C to 35°C.",
        "card_humidity_desc": "Ambient relative humidity around the crop canopy.",
        # Status labels
        "status_low": "Low",
        "status_good": "Good",
        "status_wet": "Wet",
        "status_normal": "Normal",
        "status_high": "High",
        # Sensor connectivity & simulation
        "sensor_online_label": "Sensor Online",
        "sensor_offline_label": "Sensor Offline",
        "sensor_last_updated": "Updated at",
        "alert_sensor_offline": "Soil moisture probe signal is offline. Verify device power and connection.",
        "sim_condition_label": "Telemetry & Hardware Controls",
        "sim_normal": "Normal Field Conditions",
        "sim_dry": "Dry Soil (Drought Alert)",
        "sim_wet": "Wet Soil (Post-Rain)",
        "sim_hot": "Heatwave Conditions",
        "sim_offline": "Sensor Offline / Disconnected",
        # Hardware / ESP32
        "sensor_source_simulation": "Simulated",
        "sensor_source_hardware": "ESP32 Hardware",
        "telemetry_mode_label": "Telemetry Source",
        "mode_simulation": "Software Simulation",
        "mode_hardware": "ESP32 Field Hardware",
        "battery_label": "Battery",
        "battery_low_alert": "ESP32 field node battery is low. Please charge solar battery.",
        "signal_strength_label": "Signal",
        "device_id_label": "Device ID",
        # Irrigation status
        "irrigation_water_needed": "Water Needed",
        "irrigation_not_required": "Not Required",
        "irrigation_detail_low": "Soil moisture is low for healthy crop growth.",
        "irrigation_detail_good": "Soil moisture is within a healthy range.",
        "irrigation_detail_wet": "Soil is already sufficiently wet.",
        # Assistant / Chatbot
        "assistant_title": "Ask KisanSense",
        "assistant_subtitle": "Get simple advice about your crops, soil and irrigation.",
        "assistant_welcome": "How can I help with your farm today?",
        "assistant_placeholder": "Ask about soil, crops or irrigation...",
        # Farm Profile Page
        "farm_title": "Farm Profile",
        "farm_subtitle": "Provide your farm details to get personalized recommendations across KisanSense.",
        "farm_overview_title": "Your Farm Profile",
        "farm_overview_subtitle": "Currently active settings for irrigation and chatbot advisory.",
        "farm_edit_button": "Edit Farm Profile",
        "farm_form_title": "Update Farm Details",
        "farmer_name_label": "Farmer Name",
        "farmer_name_placeholder": "e.g. Ramesh Patel",
        "farm_name_label": "Farm Name",
        "farm_name_placeholder": "e.g. Green Acres Farm",
        "location_label": "Farm Location",
        "location_placeholder": "e.g. Nashik, Maharashtra",
        "crop_label": "Main Crop",
        "crop_variety_label": "Crop Variety (Optional)",
        "crop_variety_placeholder": "e.g. Pusa Basmati, Hybrid-4",
        "growth_stage_label": "Current Growth Stage",
        "soil_type_label": "Soil Type",
        "farm_area_label": "Farm Area",
        "area_unit_label": "Area Unit",
        "irrigation_method_label": "Irrigation Method",
        "save_profile_button": "Save Farm Profile",
        "profile_saved_success": "Farm profile saved successfully!",
        "profile_saved_desc": "Your crop and soil context is now active across all KisanSense tools.",
        "val_crop_required": "Please select or specify your crop.",
        "val_area_numeric": "Farm area must be a valid positive number.",
    },
    "hi": {
        # Navigation
        "nav_home": "होम",
        "nav_farm": "खेत प्रोफ़ाइल",
        "nav_irrigation": "सिंचाई",
        "nav_vision": "पौध दृष्टि",
        "nav_assistant": "सहायक",
        "nav_alerts": "सूचनाएं",
        # Home page
        "home_tagline": "स्मार्ट खेती, आसान समाधान।",
        "home_status_active": "खेत निगरानी सक्रिय",
        "home_empty_profile_prompt": "किसानसेंस को अपने खेत अनुसार सेट करने के लिए प्रोफ़ाइल बनाएं।",
        "home_setup_profile_btn": "प्रोफ़ाइल बनाएं",
        "home_farm_active_banner": "सक्रिय खेत जानकारी",
        "home_alerts_title": "ज़रूरी सूचनाएं",
        "home_alert_water_needed": "मिट्टी की नमी कम है। सिंचाई की सलाह दी जाती है।",
        # Metric cards
        "card_soil_title": "मिट्टी की नमी",
        "card_temp_title": "तापमान",
        "card_humidity_title": "हवा की नमी",
        "card_irrigation_title": "सिंचाई स्थिति",
        "card_soil_desc": "आपके खेत के मिट्टी सेंसर से ताज़ा रीडिंग।",
        "card_temp_desc": "अधिकांश फसलों के लिए 15°C से 35°C अनुकूल तापमान है।",
        "card_humidity_desc": "फसल के आसपास की सापेक्ष वायु आर्द्रता।",
        # Status labels
        "status_low": "कम",
        "status_good": "उत्तम",
        "status_wet": "अधिक गीला",
        "status_normal": "सामान्य",
        "status_high": "अधिक",
        # Sensor connectivity & simulation
        "sensor_online_label": "सेंसर ऑनलाइन",
        "sensor_offline_label": "सेंसर ऑफलाइन",
        "sensor_last_updated": "अंतिम अपडेट",
        "alert_sensor_offline": "मिट्टी नमी सेंसर ऑफलाइन है। कृपया डिवाइस पावर और वायरिंग कनेक्शन की जांच करें।",
        "sim_condition_label": "टेलीमेट्री और हार्डवेयर सेटिंग्स",
        "sim_normal": "सामान्य खेत स्थिति",
        "sim_dry": "सूखी मिट्टी (सूखा चेतावनी)",
        "sim_wet": "गीली मिट्टी (बारिश के बाद)",
        "sim_hot": "अत्यधिक गर्मी / लू स्थिति",
        "sim_offline": "सेंसर डिस्कनेक्ट / ऑफलाइन",
        # Hardware / ESP32
        "sensor_source_simulation": "सिम्युलेटेड",
        "sensor_source_hardware": "ESP32 हार्डवेयर",
        "telemetry_mode_label": "टेलीमेट्री स्रोत",
        "mode_simulation": "सॉफ्टवेयर सिम्युलेशन",
        "mode_hardware": "ESP32 फील्ड हार्डवेयर",
        "battery_label": "बैटरी",
        "battery_low_alert": "ESP32 सेंसर की बैटरी कम है। कृपया सोलर बैटरी चार्ज करें।",
        "signal_strength_label": "सिग्नल",
        "device_id_label": "डिवाइस आईडी",
        # Irrigation status
        "irrigation_water_needed": "पानी आवश्यक",
        "irrigation_not_required": "आवश्यक नहीं",
        "irrigation_detail_low": "फसल के स्वस्थ विकास के लिए नमी कम है।",
        "irrigation_detail_good": "नमी का स्तर अनुकूल और संतुलित है।",
        "irrigation_detail_wet": "मिट्टी पहले से ही पर्याप्त नम है।",
        # Assistant / Chatbot
        "assistant_title": "किसानसेंस से पूछें",
        "assistant_subtitle": "अपनी फसल, मिट्टी और सिंचाई पर सरल सलाह पाएं।",
        "assistant_welcome": "आज मैं आपके खेत की क्या मदद कर सकता हूँ?",
        "assistant_placeholder": "मिट्टी, फसल या सिंचाई के बारे में पूछें...",
        # Farm Profile Page
        "farm_title": "खेत प्रोफ़ाइल",
        "farm_subtitle": "निजीकृत सुझावों के लिए अपने खेत का विवरण दर्ज करें।",
        "farm_overview_title": "आपकी खेत प्रोफ़ाइल",
        "farm_overview_subtitle": "सिंचाई और सहायक सलाह के लिए वर्तमान सक्रिय सेटिंग्स।",
        "farm_edit_button": "विवरण बदलें",
        "farm_form_title": "खेत का विवरण दर्ज करें",
        "farmer_name_label": "किसान का नाम",
        "farmer_name_placeholder": "उदा. रमेश पटेल",
        "farm_name_label": "खेत का नाम",
        "farm_name_placeholder": "उदा. हरियाली फार्म",
        "location_label": "खेत का स्थान",
        "location_placeholder": "उदा. नासिक, महाराष्ट्र",
        "crop_label": "मुख्य फसल",
        "crop_variety_label": "फसल की किस्म (वैकल्पिक)",
        "crop_variety_placeholder": "उदा. पूसा बासमती",
        "growth_stage_label": "विकास अवस्था",
        "soil_type_label": "मिट्टी का प्रकार",
        "farm_area_label": "खेत का क्षेत्रफल",
        "area_unit_label": "क्षेत्रफल इकाई",
        "irrigation_method_label": "सिंचाई का तरीका",
        "save_profile_button": "प्रोफ़ाइल सुरक्षित करें",
        "profile_saved_success": "खेत प्रोफ़ाइल सफलतापूर्वक सुरक्षित की गई!",
        "profile_saved_desc": "आपकी फसल और मिट्टी की जानकारी अब सभी उपकरणों में सक्रिय है।",
        "val_crop_required": "कृपया मुख्य फसल चुनें या लिखें।",
        "val_area_numeric": "खेत का क्षेत्रफल मान्य धनात्मक संख्या होनी चाहिए।",
    },
    "ta": {
        # Navigation
        "nav_home": "முகப்பு",
        "nav_farm": "பண்ணை விவரம்",
        "nav_irrigation": "நீர்ப்பாசனம்",
        "nav_vision": "பயிர் பார்வை",
        "nav_assistant": "உதவியாளர்",
        "nav_alerts": "எச்சரிக்கைகள்",
        # Home page
        "home_tagline": "புத்திசாலி விவசாயம், எளிதாக.",
        "home_status_active": "பண்ணை கண்காணிப்பு செயல்படுகிறது",
        "home_empty_profile_prompt": "உங்கள் பண்ணைக்கு ஏற்ற வழிகாட்டலைப் பெற பண்ணை விவரங்களை அமைக்கவும்.",
        "home_setup_profile_btn": "விவரங்களை அமைக்கவும்",
        "home_farm_active_banner": "செயலில் உள்ள பண்ணை தகவல்",
        "home_alerts_title": "முக்கிய எச்சரிக்கைகள்",
        "home_alert_water_needed": "மண்ணின் ஈரப்பதம் குறைவாக உள்ளது. பாசனம் தேவைப்படுகிறது.",
        # Metric cards
        "card_soil_title": "மண் ஈரப்பதம்",
        "card_temp_title": "வெப்பநிலை",
        "card_humidity_title": "காற்றின் ஈரப்பதம்",
        "card_irrigation_title": "நீர்ப்பாசனம்",
        "card_soil_desc": "உங்கள் பண்ணை சென்சாரின் சமீபத்திய அளவீடு.",
        "card_temp_desc": "பெரும்பாலான பயிர்களுக்கு 15°C முதல் 35°C வரை சிறந்தது.",
        "card_humidity_desc": "பயிரைச் சுற்றியுள்ள காற்றின் ஈரப்பதம்.",
        # Status labels
        "status_low": "குறைவு",
        "status_good": "நன்று",
        "status_wet": "அதிக ஈரம்",
        "status_normal": "இயல்பு",
        "status_high": "அதிகம்",
        # Sensor connectivity & simulation
        "sensor_online_label": "சென்சார் ஆன்லைன்",
        "sensor_offline_label": "சென்சார் ஆஃப்லைன்",
        "sensor_last_updated": "கடைசி புதுப்பிப்பு",
        "alert_sensor_offline": "மண் ஈரப்பத சென்சார் ஆஃப்லைனில் உள்ளது. சாதன இணைப்பைச் சரிபார்க்கவும்.",
        "sim_condition_label": "டெலிமெட்ரி மற்றும் வன்பொருள் அமைப்புகள்",
        "sim_normal": "சாதாரண பண்ணை நிலை",
        "sim_dry": "வறண்ட மண் (வறட்சி எச்சரிக்கை)",
        "sim_wet": "ஈரமான மண் (மழைக்குப் பின்)",
        "sim_hot": "அதிக வெப்ப நிலை",
        "sim_offline": "சென்சார் துண்டிக்கப்பட்டது / ஆஃப்லைன்",
        # Hardware / ESP32
        "sensor_source_simulation": "உருவகப்படுத்தப்பட்டது",
        "sensor_source_hardware": "ESP32 வன்பொருள்",
        "telemetry_mode_label": "டெலிமெட்ரி ஆதாரம்",
        "mode_simulation": "மென்பொருள் உருவகப்படுத்துதல்",
        "mode_hardware": "ESP32 கள வன்பொருள்",
        "battery_label": "பேட்டரி",
        "battery_low_alert": "ESP32 சென்சாரின் பேட்டரி குறைவாக உள்ளது. சோலார் பேட்டரியை சார்ஜ் செய்யவும்.",
        "signal_strength_label": "சிக்னல்",
        "device_id_label": "சாதன ஐடி",
        # Irrigation status
        "irrigation_water_needed": "தண்ணீர் தேவை",
        "irrigation_not_required": "தேவையில்லை",
        "irrigation_detail_low": "பயிர் வளர்ச்சிக்கு மண் ஈரப்பதம் குறைவாக உள்ளது.",
        "irrigation_detail_good": "மண் ஈரப்பதம் ஆரோக்கியமான வரம்பில் உள்ளது.",
        "irrigation_detail_wet": "மண் போதுமான அளவு ஈரப்பதமாக உள்ளது.",
        # Assistant / Chatbot
        "assistant_title": "கிசான்சென்ஸிடம் கேளுங்கள்",
        "assistant_subtitle": "உங்கள் பயிர், மண் மற்றும் நீர்ப்பாசனம் குறித்து எளிய ஆலோசனை பெறுங்கள்.",
        "assistant_welcome": "இன்று உங்கள் பண்ணைக்கு நான் எவ்வாறு உதவ முடியும்?",
        "assistant_placeholder": "மண், பயிர்கள் அல்லது பாசனம் பற்றி கேளுங்கள்...",
        # Farm Profile Page
        "farm_title": "பண்ணை விவரம்",
        "farm_subtitle": "துல்லியமான பரிந்துரைகளுக்கு உங்கள் பண்ணை விவரங்களை உள்ளிடவும்.",
        "farm_overview_title": "உங்கள் பண்ணை விவரம்",
        "farm_overview_subtitle": "பாசனம் மற்றும் ஆலோசனைக்கான தற்போதைய அமைப்புகள்.",
        "farm_edit_button": "விவரங்களைத் திருத்து",
        "farm_form_title": "பண்ணை விவரங்களை உள்ளிடவும்",
        "farmer_name_label": "விவசாயி பெயர்",
        "farmer_name_placeholder": "எ.கா. முருகன்",
        "farm_name_label": "பண்ணை பெயர்",
        "farm_name_placeholder": "எ.கா. பசுமை பண்ணை",
        "location_label": "இடம்",
        "location_placeholder": "எ.கா. தஞ்சாவூர், தமிழ்நாடு",
        "crop_label": "முக்கிய பயிர்",
        "crop_variety_label": "பயிர் ரகம் (விருப்பத்தேர்வு)",
        "crop_variety_placeholder": "எ.கா. பொன்னி",
        "growth_stage_label": "வளர்ச்சி நிலை",
        "soil_type_label": "மண் வகை",
        "farm_area_label": "பண்ணை பரப்பளவு",
        "area_unit_label": "பரப்பளவு அலகு",
        "irrigation_method_label": "நீர்ப்பாசன முறை",
        "save_profile_button": "விவரங்களைச் சேமிக்கவும்",
        "profile_saved_success": "பண்ணை விவரங்கள் வெற்றிகரமாக சேமிக்கப்பட்டன!",
        "profile_saved_desc": "உங்கள் பயிர் தகவல் இப்போது அனைத்து கருவிகளிலும் செயலில் உள்ளது.",
        "val_crop_required": "தயவுசெய்து முக்கிய பயிரைத் தேர்ந்தெடுக்கவும்.",
        "val_area_numeric": "பரப்பளவு செல்லுபடியாகும் எண்ணாக இருக்க வேண்டும்.",
    },
    "kn": {
        # Navigation
        "nav_home": "ಮುಖಪುಟ",
        "nav_farm": "ಕೃಷಿ ವಿವರ",
        "nav_irrigation": "ನೀರಾವರಿ",
        "nav_vision": "ಬೆಳೆ ದೃಷ್ಟಿ",
        "nav_assistant": "ಸಹಾಯಕ",
        "nav_alerts": "ಎಚ್ಚರಿಕೆಗಳು",
        # Home page
        "home_tagline": "ಸ್ಮಾರ್ಟ್ ಕೃಷಿ, ಸುಲಭ ಪರಿಹಾರ.",
        "home_status_active": "ಕೃಷಿ ಮೇಲ್ವಿಚಾರಣೆ ಸಕ್ರಿಯವಾಗಿದೆ",
        "home_empty_profile_prompt": "ಕಿಸಾನ್‌ಸೆನ್ಸ್ ವೈಯಕ್ತಿಕಗೊಳಿಸಲು ನಿಮ್ಮ ಜಮೀನಿನ ವಿವರಗಳನ್ನು ಹೊಂದಿಸಿ.",
        "home_setup_profile_btn": "ವಿವರ ಹೊಂದಿಸಿ",
        "home_farm_active_banner": "ಸಕ್ರಿಯ ಜಮೀನು ಮಾಹಿತಿ",
        "home_alerts_title": "ಪ್ರಮುಖ ಎಚ್ಚರಿಕೆಗಳು",
        "home_alert_water_needed": "ಮಣ್ಣಿನ ತೇವಾಂಶ ಕಡಿಮೆಯಾಗಿದೆ. ನೀರಾವರಿ ಅಗತ್ಯವಿದೆ.",
        # Metric cards
        "card_soil_title": "ಮಣ್ಣಿನ ತೇವಾಂಶ",
        "card_temp_title": "ತಾಪಮಾನ",
        "card_humidity_title": "ಗಾಳಿಯ ತೇವಾಂಶ",
        "card_irrigation_title": "ನೀರಾವರಿ ಸ್ಥಿತಿ",
        "card_soil_desc": "ನಿಮ್ಮ ಜಮೀನಿನ ಸಂವೇದಕದಿಂದ ಇತ್ತೀಚಿನ ಮಾಹಿತಿ.",
        "card_temp_desc": "ಹೆಚ್ಚಿನ ಬೆಳೆಗಳಿಗೆ 15°C ನಿಂದ 35°C ಸೂಕ್ತ ತಾಪಮಾನ.",
        "card_humidity_desc": "ಬೆಳೆಯ ಸುತ್ತಲಿನ ಗಾಳಿಯ ಸಾಪೇಕ್ಷ ತೇವಾಂಶ.",
        # Status labels
        "status_low": "ಕಡಿಮೆ",
        "status_good": "ಉತ್ತಮ",
        "status_wet": "ಹೆಚ್ಚು ತೇವ",
        "status_normal": "ಸಾಮಾನ್ಯ",
        "status_high": "ಹೆಚ್ಚು",
        # Sensor connectivity & simulation
        "sensor_online_label": "ಸಂವೇದಕ ಆನ್‌ಲೈನ್",
        "sensor_offline_label": "ಸಂವೇದಕ ಆಫ್‌ಲೈನ್",
        "sensor_last_updated": "ಕೊನೆಯ ನವೀಕರಣ",
        "alert_sensor_offline": "ಮಣ್ಣಿನ ತೇವಾಂಶ ಸಂವೇದಕ ಆಫ್‌ಲೈನ್‌ನಲ್ಲಿದೆ. ಸಾಧನದ ಪವರ್ ಮತ್ತು ವೈರಿಂಗ್ ಪರಿಶೀಲಿಸಿ.",
        "sim_condition_label": "ಟೆಲಿಮೆಟ್ರಿ ಮತ್ತು ಹಾರ್ಡ್‌ವೇರ್ ಸೆಟ್ಟಿಂಗ್‌ಗಳು",
        "sim_normal": "ಸಾಮಾನ್ಯ ಕೃಷಿ ಸ್ಥಿತಿ",
        "sim_dry": "ಒಣ ಮಣ್ಣು (ಬರ ಎಚ್ಚರಿಕೆ)",
        "sim_wet": "ತೇವಾಂಶದ ಮಣ್ಣು (ಮಳೆಯ ನಂತರ)",
        "sim_hot": "ತೀವ್ರ ತಾಪಮಾನ ಸ್ಥಿತಿ",
        "sim_offline": "ಸಂವೇದಕ ಸಂಪರ್ಕ ಕಡಿತಗೊಂಡಿದೆ / ಆಫ್‌ಲೈನ್",
        # Hardware / ESP32
        "sensor_source_simulation": "ಅನುಕರಿಸಲಾಗಿದೆ",
        "sensor_source_hardware": "ESP32 ಹಾರ್ಡ್‌ವೇರ್",
        "telemetry_mode_label": "ಟೆಲಿಮೆಟ್ರಿ ಮೂಲ",
        "mode_simulation": "ಸಾಫ್ಟ್‌ವೇರ್ ಅನುಕರಣೆ",
        "mode_hardware": "ESP32 ಕ್ಷೇತ್ರ ಹಾರ್ಡ್‌ವೇರ್",
        "battery_label": "ಬ್ಯಾಟರಿ",
        "battery_low_alert": "ESP32 ಸಂವೇದಕದ ಬ್ಯಾಟರಿ ಕಡಿಮೆಯಾಗಿದೆ. ದಯವಿಟ್ಟು ಸೌರ ಬ್ಯಾಟರಿಯನ್ನು ಚಾರ್ಜ್ ಮಾಡಿ.",
        "signal_strength_label": "ಸಿಗ್ನಲ್",
        "device_id_label": "ಸಾಧನ ಐಡಿ",
        # Irrigation status
        "irrigation_water_needed": "ನೀರು ಅಗತ್ಯವಿದೆ",
        "irrigation_not_required": "ಅಗತ್ಯವಿಲ್ಲ",
        "irrigation_detail_low": "ಆರೋಗ್ಯಕರ ಬೆಳವಣಿಗೆಗೆ ಮಣ್ಣಿನ ತೇವಾಂಶ ಕಡಿಮೆಯಾಗಿದೆ.",
        "irrigation_detail_good": "ಮಣ್ಣಿನ ತೇವಾಂಶ ಸಮತೋಲನದಲ್ಲಿದೆ.",
        "irrigation_detail_wet": "ಮಣ್ಣಿನಲ್ಲಿ ಈಗಾಗಲೇ ಸಾಕಷ್ಟು ತೇವಾಂಶವಿದೆ.",
        # Assistant / Chatbot
        "assistant_title": "ಕಿಸಾನ್‌ಸೆನ್ಸ್ ಬಳಿ ಕೇಳಿ",
        "assistant_subtitle": "ಬೆಳೆ, ಮಣ್ಣು ಮತ್ತು ನೀರಾವರಿ ಬಗ್ಗೆ ಸರಳ ಸಲಹೆ ಪಡೆಯಿರಿ.",
        "assistant_welcome": "ಇಂದು ನಿಮ್ಮ ಜಮೀನಿಗೆ ನಾನು ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
        "assistant_placeholder": "ಮಣ್ಣು, ಬೆಳೆ ಅಥವಾ ನೀರಾವರಿ ಬಗ್ಗೆ ಕೇಳಿ...",
        # Farm Profile Page
        "farm_title": "ಕೃಷಿ ವಿವರ",
        "farm_subtitle": "ನಿಖರವಾದ ಸಲಹೆಗಳಿಗಾಗಿ ನಿಮ್ಮ ಜಮೀನಿನ ವಿವರಗಳನ್ನು ನಮೂದಿಸಿ.",
        "farm_overview_title": "ನಿಮ್ಮ ಜಮೀನಿನ ವಿವರ",
        "farm_overview_subtitle": "ನೀರಾವರಿ ಮತ್ತು ಸಲಹೆಗಾಗಿ ಸಕ್ರಿಯವಾಗಿರುವ ಸೆಟ್ಟಿಂಗ್‌ಗಳು.",
        "farm_edit_button": "ವಿವರ ಬದಲಾಯಿಸಿ",
        "farm_form_title": "ಜಮೀನಿನ ವಿವರಗಳನ್ನು ನಮೂದಿಸಿ",
        "farmer_name_label": "ರೈತರ ಹೆಸರು",
        "farmer_name_placeholder": "ಉದಾ. ಮಂಜುನಾಥ್",
        "farm_name_label": "ಜಮೀನಿನ ಹೆಸರು",
        "farm_name_placeholder": "ಉದಾ. ಹಸಿರು ಕೃಷಿ",
        "location_label": "ಸ್ಥಳ",
        "location_placeholder": "ಉದಾ. ಮಂಡ್ಯ, ಕರ್ನಾಟಕ",
        "crop_label": "ಮುಖ್ಯ ಬೆಳೆ",
        "crop_variety_label": "ಬೆಳೆ ತಳಿ (ಐಚ್ಛಿಕ)",
        "crop_variety_placeholder": "ಉದಾ. ಸೋನಾ ಮಸೂರಿ",
        "growth_stage_label": "ಬೆಳವಣಿಗೆ ಹಂತ",
        "soil_type_label": "ಮಣ್ಣಿನ ವಿಧ",
        "farm_area_label": "ಜಮೀನಿನ ವಿಸ್ತೀರ್ಣ",
        "area_unit_label": "ವಿಸ್ತೀರ್ಣ ಘಟಕ",
        "irrigation_method_label": "ನೀರಾವರಿ ವಿಧಾನ",
        "save_profile_button": "ವಿವರಗಳನ್ನು ಉಳಿಸಿ",
        "profile_saved_success": "ಜಮೀನಿನ ವಿವರಗಳನ್ನು ಯಶಸ್ವಿಯಾಗಿ ಉಳಿಸಲಾಗಿದೆ!",
        "profile_saved_desc": "ನಿಮ್ಮ ಬೆಳೆ ಮತ್ತು ಮಣ್ಣಿನ ಮಾಹಿತಿ ಈಗ ಎಲ್ಲಾ ವಿಭಾಗಗಳಲ್ಲಿ ಸಕ್ರಿಯವಾಗಿದೆ.",
        "val_crop_required": "ದಯವಿಟ್ಟು ಮುಖ್ಯ ಬೆಳೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ.",
        "val_area_numeric": "ವಿಸ್ತೀರ್ಣವು ಮಾನ್ಯ ಧನಾತ್ಮಕ ಸಂಖ್ಯೆಯಾಗಿರಬೇಕು.",
    },
}


def get_current_lang() -> str:
    """Return active language from session state or DEFAULT_LANG."""
    try:
        import streamlit as st

        if hasattr(st, "session_state") and "lang" in st.session_state:
            val = st.session_state.lang
            if val in TRANSLATIONS:
                return str(val)
    except Exception:
        pass
    return DEFAULT_LANG


def t(key: str, lang: str | None = None) -> str:
    """Look up a UI string by key.

    Falls back to current session language -> English -> key itself.
    """
    effective_lang = lang if lang is not None else get_current_lang()
    locale = TRANSLATIONS.get(effective_lang)
    if locale and key in locale:
        return locale[key]

    # Fallback to default language (English)
    fallback_locale = TRANSLATIONS.get(DEFAULT_LANG, {})
    return fallback_locale.get(key, key)
