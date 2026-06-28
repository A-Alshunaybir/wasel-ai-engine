import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone, timedelta

# --- 1. CONNECT TO FIREBASE ---
cred = credentials.Certificate("serviceAccountKey.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()
print("Connected to Firestore! Running Safe Price Update...")

now = datetime.now(timezone.utc)

# --- 2. LOGICAL TIME SLOTS ---
# Conferences: 3-day events starting next week
conf_start = now + timedelta(days=7)
conf_end = conf_start + timedelta(days=3)

# Exhibitions: Month-long events starting in two weeks
exh_start = now + timedelta(days=14)
exh_end = exh_start + timedelta(days=30)

# Heritage: Weekend events (2 days)
her_start = now + timedelta(days=4) 
her_end = her_start + timedelta(days=2)

# Institutes: 3-hour evening classes (6 PM - 9 PM)
inst_start = now.replace(hour=18, minute=0, second=0) + timedelta(days=5)
inst_end = inst_start + timedelta(hours=3)

# Libraries: 4-hour afternoon sessions (2 PM - 6 PM)
lib_start = now.replace(hour=14, minute=0, second=0) + timedelta(days=3)
lib_end = lib_start + timedelta(hours=4)

# Museums: Full day tours (9 AM - 5 PM)
mus_start = now.replace(hour=9, minute=0, second=0) + timedelta(days=1)
mus_end = mus_start + timedelta(hours=8)


# --- 3. BILINGUAL CULTURAL EVENTS DICTIONARY (30 Events) ---
mock_events = {
    # --- CONFERENCES AND FORUMS ---
    "conf_01": {
        "id": "conf_01", 
        "Title": {"en": "Riyadh International Philosophy Conference", "ar": "مؤتمر الرياض الدولي للفلسفة"},
        "About": {"en": "A global gathering of thinkers discussing the intersection of modern ethics and traditional Arab philosophy.", "ar": "تجمع عالمي للمفكرين لمناقشة التقاطع بين الأخلاق الحديثة والفلسفة العربية التقليدية."},
        "Category": {"en": "Conferences and Forums", "ar": "مؤتمرات ومنتديات"}, "Category_ID": "CONF",
        "tags": {"en": ["Philosophy", "Literature", "Education", "Culture", "Intellectual"], "ar": ["فلسفة", "أدب", "تعليم", "ثقافة", "فكري"]},
        "Rating": 4.9, "Price": {"en": "Free", "ar": "مجاني"}, 
        "Location": firestore.GeoPoint(24.6850, 46.6850), 
        "Location_Address": {"en": "King Fahad National Library", "ar": "مكتبة الملك فهد الوطنية"},
        "venue_capacity": 500, "Image_Url": "https://via.placeholder.com/400x300?text=Philosophy",
        "start_time": conf_start, "end_time": conf_end
    },
    "conf_02": {
        "id": "conf_02", 
        "Title": {"en": "Saudi Design Festival", "ar": "المهرجان السعودي للتصميم"},
        "About": {"en": "Celebrating visual design, traditional architecture, and modern aesthetic innovations in the Middle East.", "ar": "الاحتفال بالتصميم المرئي والعمارة التقليدية والابتكارات الجمالية الحديثة في الشرق الأوسط."},
        "Category": {"en": "Conferences and Forums", "ar": "مؤتمرات ومنتديات"}, "Category_ID": "CONF",
        "tags": {"en": ["Art", "Design", "Heritage", "Networking", "Architecture"], "ar": ["فن", "تصميم", "تراث", "تواصل", "عمارة"]},
        "Rating": 4.6, "Price": {"en": "50 SAR", "ar": "٥٠ ريال"}, 
        "Location": firestore.GeoPoint(24.7300, 46.6200), 
        "Location_Address": {"en": "JAX District", "ar": "حي جاكس"},
        "venue_capacity": 300, "Image_Url": "https://via.placeholder.com/400x300?text=Design+Festival",
        "start_time": conf_start, "end_time": conf_end
    },
    "conf_03": {
        "id": "conf_03", 
        "Title": {"en": "Middle East Cinema Forum", "ar": "منتدى الشرق الأوسط للسينما"},
        "About": {"en": "Filmmakers and critics discuss the evolution of Saudi cinema and regional storytelling.", "ar": "صناع الأفلام والنقاد يناقشون تطور السينما السعودية ورواية القصص الإقليمية."},
        "Category": {"en": "Conferences and Forums", "ar": "مؤتمرات ومنتديات"}, "Category_ID": "CONF",
        "tags": {"en": ["Cinema", "Art", "Storytelling", "Networking", "Culture"], "ar": ["سينما", "فن", "رواية القصص", "تواصل", "ثقافة"]},
        "Rating": 4.8, "Price": {"en": "150 SAR", "ar": "١٥٠ ريال"}, 
        "Location": firestore.GeoPoint(24.7400, 46.6100), 
        "Location_Address": {"en": "JAX District", "ar": "حي جاكس"},
        "venue_capacity": 400, "Image_Url": "https://via.placeholder.com/400x300?text=Cinema+Forum",
        "start_time": conf_start, "end_time": conf_end
    },
    "conf_04": {
        "id": "conf_04", 
        "Title": {"en": "Arabic Language & Linguistics Symposium", "ar": "ندوة اللغة العربية واللغويات"},
        "About": {"en": "Scholars dive deeply into the roots of classical Arabic, poetry preservation, and linguistic heritage.", "ar": "يتعمق العلماء في جذور اللغة العربية الفصحى، والحفاظ على الشعر، والتراث اللغوي."},
        "Category": {"en": "Conferences and Forums", "ar": "مؤتمرات ومنتديات"}, "Category_ID": "CONF",
        "tags": {"en": ["Literature", "History", "Education", "Language", "Poetry"], "ar": ["أدب", "تاريخ", "تعليم", "لغة", "شعر"]},
        "Rating": 4.9, "Price": {"en": "Free", "ar": "مجاني"}, 
        "Location": firestore.GeoPoint(24.7200, 46.6300), 
        "Location_Address": {"en": "Riyadh Public Library", "ar": "مكتبة الرياض العامة"},
        "venue_capacity": 250, "Image_Url": "https://via.placeholder.com/400x300?text=Linguistics",
        "start_time": conf_start, "end_time": conf_end
    },
    "conf_05": {
        "id": "conf_05", 
        "Title": {"en": "Saudi Cultural Heritage Summit", "ar": "قمة التراث الثقافي السعودي"},
        "About": {"en": "Policy makers and historians discuss strategies for protecting UNESCO sites and intangible heritage in the Kingdom.", "ar": "صناع السياسات والمؤرخون يناقشون استراتيجيات حماية مواقع اليونسكو والتراث غير المادي في المملكة."},
        "Category": {"en": "Conferences and Forums", "ar": "مؤتمرات ومنتديات"}, "Category_ID": "CONF",
        "tags": {"en": ["History", "Heritage", "Culture", "Networking", "Architecture"], "ar": ["تاريخ", "تراث", "ثقافة", "تواصل", "عمارة"]},
        "Rating": 4.7, "Price": {"en": "Free", "ar": "مجاني"}, 
        "Location": firestore.GeoPoint(24.6470, 46.7100), 
        "Location_Address": {"en": "King Abdul Aziz Historical Centre", "ar": "مركز الملك عبدالعزيز التاريخي"},
        "venue_capacity": 350, "Image_Url": "https://via.placeholder.com/400x300?text=Heritage+Summit",
        "start_time": conf_start, "end_time": conf_end
    },

    # --- EXHIBITIONS ---
    "exh_01": {
        "id": "exh_01", 
        "Title": {"en": "Contemporary Saudi Art Exhibition", "ar": "معرض الفن السعودي المعاصر"},
        "About": {"en": "A quiet and inspiring look at modern visual arts, showcasing upcoming local Saudi artists.", "ar": "نظرة هادئة وملهمة على الفنون البصرية الحديثة، تعرض أعمال الفنانين السعوديين المحليين الصاعدين."},
        "Category": {"en": "Exhibition and Convention", "ar": "معارض ومؤتمرات"}, "Category_ID": "EXH",
        "tags": {"en": ["Art", "Culture", "Quiet", "Local", "Visual"], "ar": ["فن", "ثقافة", "هدوء", "محلي", "مرئي"]},
        "Rating": 4.1, "Price": {"en": "100 SAR", "ar": "١٠٠ ريال"}, 
        "Location": firestore.GeoPoint(24.7300, 46.6200), 
        "Location_Address": {"en": "JAX District, Diriyah", "ar": "حي جاكس، الدرعية"},
        "venue_capacity": 150, "Image_Url": "https://via.placeholder.com/400x300?text=Art+Exhibition",
        "start_time": exh_start, "end_time": exh_end
    },
    "exh_02": {
        "id": "exh_02", 
        "Title": {"en": "Riyadh International Book Fair", "ar": "معرض الرياض الدولي للكتاب"},
        "About": {"en": "The largest gathering of publishers, authors, and literature lovers in the Kingdom.", "ar": "أكبر تجمع للناشرين والمؤلفين ومحبي الأدب في المملكة."},
        "Category": {"en": "Exhibition and Convention", "ar": "معارض ومؤتمرات"}, "Category_ID": "EXH",
        "tags": {"en": ["Literature", "Culture", "Education", "Family", "Books"], "ar": ["أدب", "ثقافة", "تعليم", "عائلة", "كتب"]},
        "Rating": 4.8, "Price": {"en": "Free", "ar": "مجاني"}, 
        "Location": firestore.GeoPoint(24.7950, 46.7320), 
        "Location_Address": {"en": "Riyadh Front", "ar": "واجهة الرياض"},
        "venue_capacity": 2000, "Image_Url": "https://via.placeholder.com/400x300?text=Book+Fair",
        "start_time": exh_start, "end_time": exh_end
    },
    "exh_03": {
        "id": "exh_03", 
        "Title": {"en": "Islamic Arts Biennale (Riyadh Edition)", "ar": "بينالي الفنون الإسلامية (نسخة الرياض)"},
        "About": {"en": "A stunning visual journey through centuries of Islamic calligraphy, geometry, and textiles.", "ar": "رحلة بصرية مذهلة عبر قرون من الخط الإسلامي والهندسة والمنسوجات."},
        "Category": {"en": "Exhibition and Convention", "ar": "معارض ومؤتمرات"}, "Category_ID": "EXH",
        "tags": {"en": ["Art", "History", "Religion", "Culture", "Visual"], "ar": ["فن", "تاريخ", "دين", "ثقافة", "مرئي"]},
        "Rating": 4.9, "Price": {"en": "50 SAR", "ar": "٥٠ ريال"}, 
        "Location": firestore.GeoPoint(24.6470, 46.7100), 
        "Location_Address": {"en": "National Museum", "ar": "المتحف الوطني"},
        "venue_capacity": 800, "Image_Url": "https://via.placeholder.com/400x300?text=Islamic+Arts",
        "start_time": exh_start, "end_time": exh_end
    },
    "exh_04": {
        "id": "exh_04", 
        "Title": {"en": "Noor Riyadh Light Festival", "ar": "احتفال نور الرياض"},
        "About": {"en": "A city-wide annual festival of light and art installations illuminating the night sky.", "ar": "مهرجان سنوي على مستوى المدينة للضوء والتركيبات الفنية التي تضيء سماء الليل."},
        "Category": {"en": "Exhibition and Convention", "ar": "معارض ومؤتمرات"}, "Category_ID": "EXH",
        "tags": {"en": ["Art", "Outdoors", "Family", "Visual", "Culture"], "ar": ["فن", "خارجي", "عائلة", "مرئي", "ثقافة"]},
        "Rating": 4.9, "Price": {"en": "Free", "ar": "مجاني"}, 
        "Location": firestore.GeoPoint(24.7115, 46.6744), 
        "Location_Address": {"en": "Various City Locations", "ar": "مواقع مختلفة في المدينة"},
        "venue_capacity": 5000, "Image_Url": "https://via.placeholder.com/400x300?text=Noor+Riyadh",
        "start_time": exh_start, "end_time": exh_end
    },
    "exh_05": {
        "id": "exh_05", 
        "Title": {"en": "Saudi Fashion & Textiles Expo", "ar": "معرض الأزياء والمنسوجات السعودية"},
        "About": {"en": "Discover the intricate embroidery, traditional garments, and modern modest fashion of the Peninsula.", "ar": "اكتشف التطريز المعقد والملابس التقليدية والأزياء المحتشمة الحديثة في شبه الجزيرة."},
        "Category": {"en": "Exhibition and Convention", "ar": "معارض ومؤتمرات"}, "Category_ID": "EXH",
        "tags": {"en": ["Fashion", "Art", "Culture", "Traditional", "Design"], "ar": ["أزياء", "فن", "ثقافة", "تقليدي", "تصميم"]},
        "Rating": 4.5, "Price": {"en": "75 SAR", "ar": "٧٥ ريال"}, 
        "Location": firestore.GeoPoint(24.9000, 46.7000), 
        "Location_Address": {"en": "Riyadh Exhibitions Center", "ar": "مركز معارض الرياض"},
        "venue_capacity": 1500, "Image_Url": "https://via.placeholder.com/400x300?text=Fashion+Expo",
        "start_time": exh_start, "end_time": exh_end
    },

    # --- HERITAGE AND TRADITION ---
    "her_01": {
        "id": "her_01", 
        "Title": {"en": "Diriyah Historical Tour", "ar": "جولة الدرعية التاريخية"},
        "About": {"en": "Walk through the birthplace of the Kingdom. A guided evening tour of the At-Turaif district.", "ar": "تجول في مسقط رأس المملكة. جولة مسائية مسحوبة بمرشد في حي الطريف."},
        "Category": {"en": "Heritage and Tradition", "ar": "تراث وتقاليد"}, "Category_ID": "HER",
        "tags": {"en": ["History", "Culture", "Outdoors", "Family", "Walking"], "ar": ["تاريخ", "ثقافة", "خارجي", "عائلة", "مشي"]},
        "Rating": 4.8, "Price": {"en": "150 SAR", "ar": "١٥٠ ريال"}, 
        "Location": firestore.GeoPoint(24.7335, 46.5755), 
        "Location_Address": {"en": "At-Turaif, Diriyah", "ar": "الطريف، الدرعية"},
        "venue_capacity": 300, "Image_Url": "https://via.placeholder.com/400x300?text=Diriyah",
        "start_time": her_start, "end_time": her_end
    },
    "her_02": {
        "id": "her_02", 
        "Title": {"en": "King Abdulaziz Falconry Festival", "ar": "مهرجان الملك عبدالعزيز للصقور"},
        "About": {"en": "Experience traditional Saudi falconry with live demonstrations and competitions.", "ar": "جرب الصقارة السعودية التقليدية مع العروض الحية والمسابقات."},
        "Category": {"en": "Heritage and Tradition", "ar": "تراث وتقاليد"}, "Category_ID": "HER",
        "tags": {"en": ["Culture", "Outdoors", "Animals", "Traditional", "Family"], "ar": ["ثقافة", "خارجي", "حيوانات", "تقليدي", "عائلة"]},
        "Rating": 4.7, "Price": {"en": "50 SAR", "ar": "٥٠ ريال"}, 
        "Location": firestore.GeoPoint(25.0000, 46.5000), 
        "Location_Address": {"en": "Malham, Riyadh", "ar": "ملهم، الرياض"},
        "venue_capacity": 1000, "Image_Url": "https://via.placeholder.com/400x300?text=Falconry",
        "start_time": her_start, "end_time": her_end
    },
    "her_03": {
        "id": "her_03", 
        "Title": {"en": "Al Janadriyah Village Experience", "ar": "تجربة قرية الجنادرية"},
        "About": {"en": "A deep dive into the heritage, crafts, and traditional dances of the Arabian Peninsula.", "ar": "غوص عميق في التراث والحرف والرقصات التقليدية لشبه الجزيرة العربية."},
        "Category": {"en": "Heritage and Tradition", "ar": "تراث وتقاليد"}, "Category_ID": "HER",
        "tags": {"en": ["History", "Culture", "Music", "Traditional", "Food"], "ar": ["تاريخ", "ثقافة", "موسيقى", "تقليدي", "طعام"]},
        "Rating": 4.9, "Price": {"en": "Free", "ar": "مجاني"}, 
        "Location": firestore.GeoPoint(24.9500, 46.7300), 
        "Location_Address": {"en": "Janadriyah", "ar": "الجنادرية"},
        "venue_capacity": 5000, "Image_Url": "https://via.placeholder.com/400x300?text=Janadriyah",
        "start_time": her_start, "end_time": her_end
    },
    "her_04": {
        "id": "her_04", 
        "Title": {"en": "Souq Al-Zal Antiques Market", "ar": "سوق الزل للتحف"},
        "About": {"en": "Explore Riyadh's oldest market for traditional carpets, ancient swords, and vintage artifacts.", "ar": "استكشف أقدم سوق في الرياض للسجاد التقليدي والسيوف القديمة والتحف العتيقة."},
        "Category": {"en": "Heritage and Tradition", "ar": "تراث وتقاليد"}, "Category_ID": "HER",
        "tags": {"en": ["History", "Culture", "Outdoors", "Shopping", "Traditional"], "ar": ["تاريخ", "ثقافة", "خارجي", "تسوق", "تقليدي"]},
        "Rating": 4.6, "Price": {"en": "Free", "ar": "مجاني"}, 
        "Location": firestore.GeoPoint(24.6300, 46.7140), 
        "Location_Address": {"en": "Diriyah, Riyadh", "ar": "الدرعية، الرياض"},
        "venue_capacity": 800, "Image_Url": "https://via.placeholder.com/400x300?text=Souq+Al-Zal",
        "start_time": her_start, "end_time": her_end
    },
    "her_05": {
        "id": "her_05", 
        "Title": {"en": "Ushaiger Heritage Village Trip", "ar": "رحلة قرية أشيقر التراثية"},
        "About": {"en": "Step back in time with a guided tour of one of the oldest mud-house villages in the Najd region.", "ar": "عد بالزمن إلى الوراء مع جولة إرشادية في واحدة من أقدم قرى البيوت الطينية في منطقة نجد."},
        "Category": {"en": "Heritage and Tradition", "ar": "تراث وتقاليد"}, "Category_ID": "HER",
        "tags": {"en": ["History", "Culture", "Outdoors", "Architecture", "Traditional"], "ar": ["تاريخ", "ثقافة", "خارجي", "عمارة", "تقليدي"]},
        "Rating": 4.8, "Price": {"en": "100 SAR", "ar": "١٠٠ ريال"}, 
        "Location": firestore.GeoPoint(25.3380, 45.3160), 
        "Location_Address": {"en": "Ushaiger, Riyadh Province", "ar": "أشيقر، منطقة الرياض"},
        "venue_capacity": 200, "Image_Url": "https://via.placeholder.com/400x300?text=Ushaiger",
        "start_time": her_start, "end_time": her_end
    },

    # --- CULTURAL INSTITUTIONS ---
    "inst_01": {
        "id": "inst_01", 
        "Title": {"en": "Cultural Institute Calligraphy Workshop", "ar": "ورشة الخط العربي بالمعهد الثقافي"},
        "About": {"en": "Learn the traditional art of Arabic calligraphy from master artists.", "ar": "تعلم الفن التقليدي للخط العربي من فنانين محترفين."},
        "Category": {"en": "Cultural Institutions", "ar": "مؤسسات ثقافية"}, "Category_ID": "INST",
        "tags": {"en": ["Art", "Education", "Culture", "Indoor", "Traditional"], "ar": ["فن", "تعليم", "ثقافة", "داخلي", "تقليدي"]},
        "Rating": 4.5, "Price": {"en": "75 SAR", "ar": "٧٥ ريال"}, 
        "Location": firestore.GeoPoint(24.6800, 46.7000), 
        "Location_Address": {"en": "National Museum Institute", "ar": "معهد المتحف الوطني"},
        "venue_capacity": 30, "Image_Url": "https://via.placeholder.com/400x300?text=Calligraphy",
        "start_time": inst_start, "end_time": inst_end
    },
    "inst_02": {
        "id": "inst_02", 
        "Title": {"en": "Misk Art Week Classes", "ar": "فصول أسبوع مسك للفنون"},
        "About": {"en": "Empowering youth through creative painting, sculpting, and storytelling sessions.", "ar": "تمكين الشباب من خلال جلسات الرسم الإبداعي والنحت ورواية القصص."},
        "Category": {"en": "Cultural Institutions", "ar": "مؤسسات ثقافية"}, "Category_ID": "INST",
        "tags": {"en": ["Art", "Education", "Youth", "Literature", "Creative"], "ar": ["فن", "تعليم", "شباب", "أدب", "إبداعي"]},
        "Rating": 4.8, "Price": {"en": "Free", "ar": "مجاني"}, 
        "Location": firestore.GeoPoint(24.7500, 46.6000), 
        "Location_Address": {"en": "Misk Art Institute", "ar": "معهد مسك للفنون"},
        "venue_capacity": 100, "Image_Url": "https://via.placeholder.com/400x300?text=Misk+Art",
        "start_time": inst_start, "end_time": inst_end
    },
    "inst_03": {
        "id": "inst_03", 
        "Title": {"en": "Saudi Music Hub: Oud Lessons", "ar": "مركز الموسيقى السعودي: دروس العود"},
        "About": {"en": "Beginner and intermediate classes focused on mastering the traditional Oud instrument.", "ar": "فصول للمبتدئين والمتوسطين تركز على إتقان آلة العود التقليدية."},
        "Category": {"en": "Cultural Institutions", "ar": "مؤسسات ثقافية"}, "Category_ID": "INST",
        "tags": {"en": ["Music", "Education", "Culture", "Traditional", "Indoor"], "ar": ["موسيقى", "تعليم", "ثقافة", "تقليدي", "داخلي"]},
        "Rating": 4.9, "Price": {"en": "150 SAR", "ar": "١٥٠ ريال"}, 
        "Location": firestore.GeoPoint(24.7100, 46.6500), 
        "Location_Address": {"en": "Saudi Music Hub", "ar": "مركز الموسيقى السعودي"},
        "venue_capacity": 20, "Image_Url": "https://via.placeholder.com/400x300?text=Oud+Lessons",
        "start_time": inst_start, "end_time": inst_end
    },
    "inst_04": {
        "id": "inst_04", 
        "Title": {"en": "TRITA Traditional Pottery Class", "ar": "درس صناعة الفخار التقليدي في المعهد الملكي"},
        "About": {"en": "Hands-on clay pottery making using heritage techniques from the Arabian Peninsula.", "ar": "صناعة الفخار الطيني عملياً باستخدام التقنيات التراثية من شبه الجزيرة العربية."},
        "Category": {"en": "Cultural Institutions", "ar": "مؤسسات ثقافية"}, "Category_ID": "INST",
        "tags": {"en": ["Art", "History", "Education", "Culture", "Traditional"], "ar": ["فن", "تاريخ", "تعليم", "ثقافة", "تقليدي"]},
        "Rating": 4.7, "Price": {"en": "120 SAR", "ar": "١٢٠ ريال"}, 
        "Location": firestore.GeoPoint(24.7300, 46.6200), 
        "Location_Address": {"en": "Royal Institute of Traditional Arts", "ar": "المعهد الملكي للفنون التقليدية"},
        "venue_capacity": 25, "Image_Url": "https://via.placeholder.com/400x300?text=Pottery",
        "start_time": inst_start, "end_time": inst_end
    },
    "inst_05": {
        "id": "inst_05", 
        "Title": {"en": "Saudi Film Academy: Directing 101", "ar": "الأكاديمية السعودية للأفلام: أساسيات الإخراج"},
        "About": {"en": "A masterclass on film directing, cinematography, and cultural storytelling for aspiring Saudi filmmakers.", "ar": "دورة متقدمة في الإخراج السينمائي والتصوير ورواية القصص الثقافية لصناع الأفلام السعوديين الطموحين."},
        "Category": {"en": "Cultural Institutions", "ar": "مؤسسات ثقافية"}, "Category_ID": "INST",
        "tags": {"en": ["Art", "Education", "Youth", "Cinema", "Creative"], "ar": ["فن", "تعليم", "شباب", "سينما", "إبداعي"]},
        "Rating": 4.8, "Price": {"en": "200 SAR", "ar": "٢٠٠ ريال"}, 
        "Location": firestore.GeoPoint(24.7400, 46.6100), 
        "Location_Address": {"en": "JAX District", "ar": "حي جاكس"},
        "venue_capacity": 40, "Image_Url": "https://via.placeholder.com/400x300?text=Film+Academy",
        "start_time": inst_start, "end_time": inst_end
    },

    # --- LIBRARIES ---
    "lib_01": {
        "id": "lib_01", 
        "Title": {"en": "King Fahad Library Rare Manuscripts Display", "ar": "عرض المخطوطات النادرة بمكتبة الملك فهد"},
        "About": {"en": "A special viewing of rare historical Islamic manuscripts.", "ar": "عرض خاص للمخطوطات الإسلامية التاريخية النادرة."},
        "Category": {"en": "Libraries", "ar": "مكتبات"}, "Category_ID": "LIB",
        "tags": {"en": ["History", "Quiet", "Education", "Indoor", "Literature"], "ar": ["تاريخ", "هدوء", "تعليم", "داخلي", "أدب"]},
        "Rating": 4.2, "Price": {"en": "Free", "ar": "مجاني"}, 
        "Location": firestore.GeoPoint(24.6850, 46.6850), 
        "Location_Address": {"en": "King Fahad National Library", "ar": "مكتبة الملك فهد الوطنية"},
        "venue_capacity": 200, "Image_Url": "https://via.placeholder.com/400x300?text=Rare+Manuscripts",
        "start_time": lib_start, "end_time": lib_end
    },
    "lib_02": {
        "id": "lib_02", 
        "Title": {"en": "Arabic Poetry Recital Night", "ar": "أمسية إلقاء الشعر العربي"},
        "About": {"en": "An evening of classic and modern Arabic poetry readings in the main atrium.", "ar": "أمسية من القراءات الشعرية العربية الكلاسيكية والحديثة في الردهة الرئيسية."},
        "Category": {"en": "Libraries", "ar": "مكتبات"}, "Category_ID": "LIB",
        "tags": {"en": ["Literature", "Culture", "Art", "Quiet", "Indoor"], "ar": ["أدب", "ثقافة", "فن", "هدوء", "داخلي"]},
        "Rating": 4.6, "Price": {"en": "Free", "ar": "مجاني"}, 
        "Location": firestore.GeoPoint(24.6850, 46.6850), 
        "Location_Address": {"en": "King Fahad National Library", "ar": "مكتبة الملك فهد الوطنية"},
        "venue_capacity": 80, "Image_Url": "https://via.placeholder.com/400x300?text=Poetry",
        "start_time": lib_start, "end_time": lib_end
    },
    "lib_03": {
        "id": "lib_03", 
        "Title": {"en": "Children's Storytelling Weekend", "ar": "عطلة نهاية الأسبوع لقصص الأطفال"},
        "About": {"en": "Interactive reading sessions for kids featuring classic Saudi folktales and oral histories.", "ar": "جلسات قراءة تفاعلية للأطفال تتميز بالقصص الشعبية السعودية الكلاسيكية والتاريخ الشفوي."},
        "Category": {"en": "Libraries", "ar": "مكتبات"}, "Category_ID": "LIB",
        "tags": {"en": ["Literature", "Family", "Education", "Indoor", "Youth"], "ar": ["أدب", "عائلة", "تعليم", "داخلي", "شباب"]},
        "Rating": 4.8, "Price": {"en": "Free", "ar": "مجاني"}, 
        "Location": firestore.GeoPoint(24.7200, 46.6300), 
        "Location_Address": {"en": "Riyadh Public Library", "ar": "مكتبة الرياض العامة"},
        "venue_capacity": 50, "Image_Url": "https://via.placeholder.com/400x300?text=Storytelling",
        "start_time": lib_start, "end_time": lib_end
    },
    "lib_04": {
        "id": "lib_04", 
        "Title": {"en": "Digital Archives Launch Event", "ar": "فعالية إطلاق الأرشيف الرقمي"},
        "About": {"en": "A presentation on navigating the new digital database of historical Saudi documents and royal decrees.", "ar": "عرض تقديمي حول التنقل في قاعدة البيانات الرقمية الجديدة للوثائق السعودية التاريخية والمراسيم الملكية."},
        "Category": {"en": "Libraries", "ar": "مكتبات"}, "Category_ID": "LIB",
        "tags": {"en": ["History", "Education", "Quiet", "Literature", "Culture"], "ar": ["تاريخ", "تعليم", "هدوء", "أدب", "ثقافة"]},
        "Rating": 4.0, "Price": {"en": "Free", "ar": "مجاني"}, 
        "Location": firestore.GeoPoint(24.6850, 46.6850), 
        "Location_Address": {"en": "King Fahad National Library", "ar": "مكتبة الملك فهد الوطنية"},
        "venue_capacity": 100, "Image_Url": "https://via.placeholder.com/400x300?text=Digital+Archive",
        "start_time": lib_start, "end_time": lib_end
    },
    "lib_05": {
        "id": "lib_05", 
        "Title": {"en": "Classic Arabic Literature Reading Club", "ar": "نادي قراءة الأدب العربي الكلاسيكي"},
        "About": {"en": "A weekly gathering to discuss foundational works of Arabic literature, from Al-Mutanabbi to Naguib Mahfouz.", "ar": "تجمع أسبوعي لمناقشة الأعمال التأسيسية للأدب العربي، من المتنبي إلى نجيب محفوظ."},
        "Category": {"en": "Libraries", "ar": "مكتبات"}, "Category_ID": "LIB",
        "tags": {"en": ["Literature", "Education", "Culture", "Quiet", "Indoor"], "ar": ["أدب", "تعليم", "ثقافة", "هدوء", "داخلي"]},
        "Rating": 4.9, "Price": {"en": "Free", "ar": "مجاني"}, 
        "Location": firestore.GeoPoint(24.7200, 46.6300), 
        "Location_Address": {"en": "Riyadh Public Library", "ar": "مكتبة الرياض العامة"},
        "venue_capacity": 30, "Image_Url": "https://via.placeholder.com/400x300?text=Reading+Club",
        "start_time": lib_start, "end_time": lib_end
    },

    # --- MUSEUMS ---
    "mus_01": {
        "id": "mus_01", 
        "Title": {"en": "National Museum of Saudi Arabia Tour", "ar": "جولة المتحف الوطني السعودي"},
        "About": {"en": "Explore eight interactive halls detailing the complete history of the Arabian Peninsula.", "ar": "استكشف ثماني قاعات تفاعلية تفصل التاريخ الكامل لشبه الجزيرة العربية."},
        "Category": {"en": "Museums", "ar": "متاحف"}, "Category_ID": "MUS",
        "tags": {"en": ["History", "Family", "Culture", "Indoor", "Education"], "ar": ["تاريخ", "عائلة", "ثقافة", "داخلي", "تعليم"]},
        "Rating": 4.9, "Price": {"en": "10 SAR", "ar": "١٠ ريال"}, 
        "Location": firestore.GeoPoint(24.6470, 46.7100), 
        "Location_Address": {"en": "King Abdul Aziz Historical Centre", "ar": "مركز الملك عبدالعزيز التاريخي"},
        "venue_capacity": 800, "Image_Url": "https://via.placeholder.com/400x300?text=National+Museum",
        "start_time": mus_start, "end_time": mus_end
    },
    "mus_02": {
        "id": "mus_02", 
        "Title": {"en": "Al Masmak Palace Exhibition", "ar": "معرض قصر المصمك"},
        "About": {"en": "Walk through the mud-brick fortress that played a vital role in the Kingdom's unification.", "ar": "تجول في قلعة الطوب اللبن التي لعبت دوراً حيوياً في توحيد المملكة."},
        "Category": {"en": "Museums", "ar": "متاحف"}, "Category_ID": "MUS",
        "tags": {"en": ["History", "Architecture", "Culture", "Family", "Indoor"], "ar": ["تاريخ", "عمارة", "ثقافة", "عائلة", "داخلي"]},
        "Rating": 4.6, "Price": {"en": "Free", "ar": "مجاني"}, 
        "Location": firestore.GeoPoint(24.6310, 46.7130), 
        "Location_Address": {"en": "Al Diriyah, Riyadh", "ar": "الدرعية، الرياض"},
        "venue_capacity": 300, "Image_Url": "https://via.placeholder.com/400x300?text=Al+Masmak",
        "start_time": mus_start, "end_time": mus_end
    },
    "mus_03": {
        "id": "mus_03", 
        "Title": {"en": "Diriyah Contemporary Art Biennale", "ar": "بينالي الدرعية للفن المعاصر"},
        "About": {"en": "Showcasing transformative works from Saudi and international artists in historical Diriyah.", "ar": "عرض أعمال تحويلية من فنانين سعوديين ودوليين في الدرعية التاريخية."},
        "Category": {"en": "Museums", "ar": "متاحف"}, "Category_ID": "MUS",
        "tags": {"en": ["Art", "Culture", "Visual", "History", "Family"], "ar": ["فن", "ثقافة", "مرئي", "تاريخ", "عائلة"]},
        "Rating": 4.8, "Price": {"en": "75 SAR", "ar": "٧٥ ريال"}, 
        "Location": firestore.GeoPoint(24.7330, 46.5750), 
        "Location_Address": {"en": "JAX District", "ar": "حي جاكس"},
        "venue_capacity": 600, "Image_Url": "https://via.placeholder.com/400x300?text=Art+Biennale",
        "start_time": mus_start, "end_time": mus_end
    },
    "mus_04": {
        "id": "mus_04", 
        "Title": {"en": "Saudi National Costume Exhibition", "ar": "معرض الأزياء الوطنية السعودية"},
        "About": {"en": "A vibrant display of traditional attire representing the diverse regions of the Kingdom.", "ar": "عرض نابض بالحياة للأزياء التقليدية التي تمثل المناطق المتنوعة في المملكة."},
        "Category": {"en": "Museums", "ar": "متاحف"}, "Category_ID": "MUS",
        "tags": {"en": ["Culture", "History", "Art", "Traditional", "Indoor"], "ar": ["ثقافة", "تاريخ", "فن", "تقليدي", "داخلي"]},
        "Rating": 4.5, "Price": {"en": "20 SAR", "ar": "٢٠ ريال"}, 
        "Location": firestore.GeoPoint(24.6470, 46.7100), 
        "Location_Address": {"en": "National Museum", "ar": "المتحف الوطني"},
        "venue_capacity": 400, "Image_Url": "https://via.placeholder.com/400x300?text=Costume+Exhibition",
        "start_time": mus_start, "end_time": mus_end
    },
    "mus_05": {
        "id": "mus_05", 
        "Title": {"en": "The Arabian Horse Museum Tour", "ar": "جولة متحف الخيل العربية"},
        "About": {"en": "Explore the majestic history, lineage, and cultural significance of the purebred Arabian horse.", "ar": "استكشف التاريخ المهيب والنسب والأهمية الثقافية للخيل العربية الأصيلة."},
        "Category": {"en": "Museums", "ar": "متاحف"}, "Category_ID": "MUS",
        "tags": {"en": ["History", "Culture", "Animals", "Family", "Heritage"], "ar": ["تاريخ", "ثقافة", "حيوانات", "عائلة", "تراث"]},
        "Rating": 4.8, "Price": {"en": "30 SAR", "ar": "٣٠ ريال"}, 
        "Location": firestore.GeoPoint(24.5830, 46.6330), 
        "Location_Address": {"en": "Dirab, Riyadh", "ar": "ديراب، الرياض"},
        "venue_capacity": 250, "Image_Url": "https://via.placeholder.com/400x300?text=Arabian+Horse",
        "start_time": mus_start, "end_time": mus_end
    }
}

# --- 4. UPDATE PRICES ONLY (SAFE FOR TEAMMATE'S IMAGES) ---
for doc_id, event_data in mock_events.items():
    price_en = event_data["Price"]["en"]
    price_ar = event_data["Price"]["ar"]
    
    # 1. Clean the English price
    if price_en == "Free":
        clean_en = "0"
    else:
        clean_en = "".join(filter(str.isdigit, price_en))
        
    # 2. Clean the Arabic price
    if price_ar == "مجاني":
        clean_ar = "0"
    else:
        clean_ar = "".join(filter(str.isdigit, price_ar))

    # 3. Use .update() to ONLY push the new prices
    try:
        db.collection("Events").document(doc_id).update({
            "Price": {
                "en": clean_en,
                "ar": clean_ar
            }
        })
        print(f"Safe Updated: {doc_id} to {clean_en}")
    except Exception as e:
        print(f"Error updating {doc_id}. Has it been deleted? Error: {e}")

print("\nSuccess! Prices are now clean numbers, and your teammate's images are completely safe.")