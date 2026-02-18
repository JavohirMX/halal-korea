"""
Curated daily Ramadan duas and fasting tips.
Each entry is keyed by day number (1-30).
"""
from django.utils.translation import gettext_lazy as _


RAMADAN_DUAS = {
    1: {
        "arabic": "اللَّهُمَّ بَارِكْ لَنَا فِي رَمَضَان",
        "transliteration": "Allahumma baarik lana fi Ramadan",
        "translation": _("O Allah, bless us in Ramadan."),
    },
    2: {
        "arabic": "اللَّهُمَّ إِنِّي أَسْأَلُكَ الْجَنَّةَ وَأَعُوذُ بِكَ مِنَ النَّار",
        "transliteration": "Allahumma inni as'aluka al-Jannah wa a'udhu bika min an-Naar",
        "translation": _("O Allah, I ask You for Paradise and seek refuge from the Fire."),
    },
    3: {
        "arabic": "اللَّهُمَّ إِنَّكَ عَفُوٌّ تُحِبُّ الْعَفْوَ فَاعْفُ عَنِّي",
        "transliteration": "Allahumma innaka 'afuwwun tuhibbul-'afwa fa'fu 'anni",
        "translation": _("O Allah, You are the Pardoner and You love to pardon, so pardon me."),
    },
    4: {
        "arabic": "رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّار",
        "transliteration": "Rabbana aatina fid-dunya hasanatan wa fil-aakhirati hasanatan wa qina 'adhab an-Naar",
        "translation": _("Our Lord, give us good in this world and good in the Hereafter, and save us from the Fire."),
    },
    5: {
        "arabic": "اللَّهُمَّ اغْفِرْ لِي ذَنْبِي كُلَّهُ دِقَّهُ وَجِلَّهُ وَأَوَّلَهُ وَآخِرَه",
        "transliteration": "Allahumma-ghfir li dhanbi kullahu diqqahu wa jillahu wa awwalahu wa aakhirahu",
        "translation": _("O Allah, forgive all my sins, small and great, first and last."),
    },
    6: {
        "arabic": "اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْهَمِّ وَالْحَزَن",
        "transliteration": "Allahumma inni a'udhu bika minal-hammi wal-hazan",
        "translation": _("O Allah, I seek refuge in You from worry and grief."),
    },
    7: {
        "arabic": "رَبِّ اشْرَحْ لِي صَدْرِي وَيَسِّرْ لِي أَمْرِي",
        "transliteration": "Rabbi-shrah li sadri wa yassir li amri",
        "translation": _("My Lord, expand my chest and ease my affair."),
    },
    8: {
        "arabic": "اللَّهُمَّ أَعِنِّي عَلَى ذِكْرِكَ وَشُكْرِكَ وَحُسْنِ عِبَادَتِك",
        "transliteration": "Allahumma a'inni 'ala dhikrika wa shukrika wa husni 'ibadatik",
        "translation": _("O Allah, help me to remember You, thank You, and worship You well."),
    },
    9: {
        "arabic": "اللَّهُمَّ تَقَبَّلْ مِنَّا صِيَامَنَا وَقِيَامَنَا",
        "transliteration": "Allahumma taqabbal minna siyamana wa qiyamana",
        "translation": _("O Allah, accept from us our fasting and our prayers."),
    },
    10: {
        "arabic": "اللَّهُمَّ ارْزُقْنِي حُبَّكَ وَحُبَّ مَنْ يُحِبُّك",
        "transliteration": "Allahumma-rzuqni hubbaka wa hubba man yuhibbuk",
        "translation": _("O Allah, grant me Your love and the love of those who love You."),
    },
    11: {
        "arabic": "رَبَّنَا لَا تُزِغْ قُلُوبَنَا بَعْدَ إِذْ هَدَيْتَنَا",
        "transliteration": "Rabbana la tuzigh quloobana ba'da idh hadaytana",
        "translation": _("Our Lord, do not let our hearts deviate after You have guided us."),
    },
    12: {
        "arabic": "اللَّهُمَّ اجْعَلْنِي مِنَ التَّوَّابِينَ وَاجْعَلْنِي مِنَ الْمُتَطَهِّرِين",
        "transliteration": "Allahumma-j'alni minat-tawwabina waj'alni minal-mutatahhirin",
        "translation": _("O Allah, make me among those who repent and those who purify themselves."),
    },
    13: {
        "arabic": "اللَّهُمَّ بَلِّغْنَا لَيْلَةَ الْقَدْر",
        "transliteration": "Allahumma ballighna Laylatal-Qadr",
        "translation": _("O Allah, let us reach the Night of Decree."),
    },
    14: {
        "arabic": "اللَّهُمَّ اهْدِنِي وَسَدِّدْنِي",
        "transliteration": "Allahumma-hdini wa saddidni",
        "translation": _("O Allah, guide me and keep me on the right path."),
    },
    15: {
        "arabic": "رَبِّ أَوْزِعْنِي أَنْ أَشْكُرَ نِعْمَتَكَ الَّتِي أَنْعَمْتَ عَلَيَّ",
        "transliteration": "Rabbi awzi'ni an ashkura ni'matakal-lati an'amta 'alayya",
        "translation": _("My Lord, inspire me to be grateful for Your favors which You have bestowed upon me."),
    },
    16: {
        "arabic": "اللَّهُمَّ إِنِّي أَسْأَلُكَ عِلْمًا نَافِعًا وَرِزْقًا طَيِّبًا وَعَمَلًا مُتَقَبَّلًا",
        "transliteration": "Allahumma inni as'aluka 'ilman naafi'an wa rizqan tayyiban wa 'amalan mutaqabbalan",
        "translation": _("O Allah, I ask You for beneficial knowledge, good provision, and accepted deeds."),
    },
    17: {
        "arabic": "اللَّهُمَّ أَصْلِحْ لِي دِينِي الَّذِي هُوَ عِصْمَةُ أَمْرِي",
        "transliteration": "Allahumma aslih li deeni-lladhi huwa 'ismatu amri",
        "translation": _("O Allah, set right my religion which is the safeguard of my affairs."),
    },
    18: {
        "arabic": "رَبَّنَا هَبْ لَنَا مِنْ أَزْوَاجِنَا وَذُرِّيَّاتِنَا قُرَّةَ أَعْيُن",
        "transliteration": "Rabbana hab lana min azwajina wa dhurriyyatina qurrata a'yun",
        "translation": _("Our Lord, grant us from our spouses and offspring comfort to our eyes."),
    },
    19: {
        "arabic": "اللَّهُمَّ اجْعَلْ الْقُرْآنَ رَبِيعَ قَلْبِي",
        "transliteration": "Allahumma-j'alil-Qur'ana rabi'a qalbi",
        "translation": _("O Allah, make the Quran the spring of my heart."),
    },
    20: {
        "arabic": "اللَّهُمَّ أَعْتِقْ رِقَابَنَا مِنَ النَّار",
        "transliteration": "Allahumma a'tiq riqabana min an-Naar",
        "translation": _("O Allah, free our necks from the Fire."),
    },
    21: {
        "arabic": "اللَّهُمَّ إِنَّكَ عَفُوٌّ كَرِيمٌ تُحِبُّ الْعَفْوَ فَاعْفُ عَنِّي",
        "transliteration": "Allahumma innaka 'afuwwun karimun tuhibbul-'afwa fa'fu 'anni",
        "translation": _("O Allah, You are the Generous Pardoner who loves to pardon, so pardon me."),
    },
    22: {
        "arabic": "اللَّهُمَّ ثَبِّتْنِي عَلَى دِينِك",
        "transliteration": "Allahumma thabbitni 'ala dinik",
        "translation": _("O Allah, keep me steadfast upon Your religion."),
    },
    23: {
        "arabic": "اللَّهُمَّ اجْعَلْ خَيْرَ عُمْرِي آخِرَهُ وَخَيْرَ عَمَلِي خَوَاتِمَه",
        "transliteration": "Allahumma-j'al khayra 'umri aakhirahu wa khayra 'amali khawatimah",
        "translation": _("O Allah, make the best of my life its end, and the best of my deeds the final ones."),
    },
    24: {
        "arabic": "اللَّهُمَّ ارْحَمْنِي بِتَرْكِ الْمَعَاصِي أَبَدًا مَا أَبْقَيْتَنِي",
        "transliteration": "Allahumma-rhamni bi tarkil-ma'asi abadan ma abqaytani",
        "translation": _("O Allah, have mercy on me by keeping me away from sins for as long as You let me live."),
    },
    25: {
        "arabic": "اللَّهُمَّ اجْعَلْنِي مِمَّنْ يَقُومُ لَيْلَةَ الْقَدْرِ إِيمَانًا وَاحْتِسَابًا",
        "transliteration": "Allahumma-j'alni mimman yaqumu Laylatal-Qadri imanan wahtisaban",
        "translation": _("O Allah, make me among those who stand in prayer on the Night of Decree with faith and hope of reward."),
    },
    26: {
        "arabic": "اللَّهُمَّ إِنِّي أَسْأَلُكَ الثَّبَاتَ فِي الْأَمْر",
        "transliteration": "Allahumma inni as'alukat-thabata fil-amr",
        "translation": _("O Allah, I ask You for steadfastness in all affairs."),
    },
    27: {
        "arabic": "اللَّهُمَّ إِنَّكَ عَفُوٌّ تُحِبُّ الْعَفْوَ فَاعْفُ عَنِّي",
        "transliteration": "Allahumma innaka 'afuwwun tuhibbul-'afwa fa'fu 'anni",
        "translation": _("O Allah, You are the Pardoner and You love to pardon, so pardon me."),
    },
    28: {
        "arabic": "اللَّهُمَّ تَقَبَّلْ مِنَّا إِنَّكَ أَنْتَ السَّمِيعُ الْعَلِيم",
        "transliteration": "Allahumma taqabbal minna innaka antas-Sami'ul-'Alim",
        "translation": _("O Allah, accept from us; indeed You are the All-Hearing, All-Knowing."),
    },
    29: {
        "arabic": "اللَّهُمَّ اجْعَلْنَا مِنْ عُتَقَائِكَ مِنَ النَّار",
        "transliteration": "Allahumma-j'alna min 'utaqa'ika min an-Naar",
        "translation": _("O Allah, make us among those You have freed from the Fire."),
    },
    30: {
        "arabic": "اللَّهُمَّ تَقَبَّلْ مِنَّا رَمَضَانَ وَأَعِدْهُ عَلَيْنَا أَعْوَامًا عَدِيدَة",
        "transliteration": "Allahumma taqabbal minna Ramadan wa a'idhu 'alayna a'waman 'adidah",
        "translation": _("O Allah, accept our Ramadan and return it to us for many years to come."),
    },
}


RAMADAN_TIPS = {
    1: _("Begin Ramadan with a sincere intention (niyyah) for fasting. The intention should be made in the heart before Fajr."),
    2: _("Have a nutritious suhoor -- include complex carbohydrates, protein, and plenty of water to stay energized."),
    3: _("Break your fast with dates and water, following the Sunnah of the Prophet (peace be upon him)."),
    4: _("Increase your Quran recitation. Many Muslims aim to complete the entire Quran during Ramadan."),
    5: _("Avoid overeating at iftar. Eat moderately and give your body time to adjust."),
    6: _("Give charity regularly during Ramadan. Even a small amount each day carries great reward."),
    7: _("Perform Tarawih prayers at the mosque to strengthen your community bonds."),
    8: _("Guard your tongue from backbiting, gossip, and harsh words -- fasting includes the tongue."),
    9: _("Make a Ramadan schedule: set specific times for Quran, dhikr, dua, and rest."),
    10: _("Stay hydrated between iftar and suhoor. Drink water regularly, not all at once."),
    11: _("Use the time before iftar for dua -- it is one of the times when supplications are accepted."),
    12: _("Take a short nap after Dhuhr if possible to help manage energy during fasting."),
    13: _("Feed others who are fasting. The reward for feeding a fasting person is equal to their fast."),
    14: _("Reduce screen time and social media to focus more on worship and reflection."),
    15: _("Reflect on the halfway point of Ramadan. Renew your intentions and increase your efforts."),
    16: _("Practice patience (sabr). Fasting trains us to be patient in all aspects of life."),
    17: _("Attend Islamic study circles or lectures to deepen your understanding during Ramadan."),
    18: _("Remember those less fortunate. Calculate and pay your Zakat during this blessed month."),
    19: _("As you approach the last ten nights, plan to increase your worship significantly."),
    20: _("Begin preparing for the last ten nights. Some people perform i'tikaf (spiritual retreat) at the mosque."),
    21: _("The last ten nights have begun. Seek Laylatul Qadr (the Night of Decree) in the odd nights."),
    22: _("Make a special dua list for the last ten nights and ask Allah sincerely."),
    23: _("This could be Laylatul Qadr. Worship as if this is the night -- pray, make dua, and recite Quran."),
    24: _("Continue your extra worship. Keep up the momentum through each remaining night."),
    25: _("One of the most likely nights for Laylatul Qadr. Increase your prayers and supplications."),
    26: _("Prepare your Zakat al-Fitr before Eid. It must be given before the Eid prayer."),
    27: _("Traditionally considered the most likely Laylatul Qadr. Dedicate this night to worship."),
    28: _("Begin planning for Eid. Prepare your clothes and arrange Eid greetings for loved ones."),
    29: _("As Ramadan nears its end, ask Allah to accept your fasting and good deeds."),
    30: _("On the last day, recite the Eid takbeer and prepare for tomorrow's celebration. Eid Mubarak!"),
}


def get_dua_for_day(day_number):
    """Returns the dua dict for a given Ramadan day, with fallback to day 1."""
    return RAMADAN_DUAS.get(day_number, RAMADAN_DUAS[1])


def get_tip_for_day(day_number):
    """Returns the tip string for a given Ramadan day, with fallback to day 1."""
    return RAMADAN_TIPS.get(day_number, RAMADAN_TIPS[1])
