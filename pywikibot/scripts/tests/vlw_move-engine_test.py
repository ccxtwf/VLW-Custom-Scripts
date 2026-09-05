import pytest
from scripts.vlw_move_engine import EngineMoverBot

bot = EngineMoverBot(old_engine="foo", new_engine="bar")

@pytest.mark.parametrize(
  "text, match_underscore, case_insensitive_first_char, expected",
  [
      ("Luo Tianyi", False, False, "Luo +Tianyi"),
      ("Luo Tianyi (ACE Virtual Singer)", False, False, "Luo +Tianyi +\\(ACE +Virtual +Singer\\)"),
      ("Luo Tianyi", True, False, "Luo[ _]+Tianyi"),
      ("Luo Tianyi (ACE Virtual Singer)", True, False, "Luo[ _]+Tianyi[ _]+\\(ACE[ _]+Virtual[ _]+Singer\\)"),
      ("Luo Tianyi", False, True, "[lL]uo +Tianyi"),
      ("Luo Tianyi (ACE Virtual Singer)", False, True, "[lL]uo +Tianyi +\\(ACE +Virtual +Singer\\)"),
      ("Luo Tianyi", True, True, "[lL]uo[ _]+Tianyi"),
      ("Luo Tianyi (ACE Virtual Singer)", True, True, "[lL]uo[ _]+Tianyi[ _]+\\(ACE[ _]+Virtual[ _]+Singer\\)"),
  ]
)
def test_prepare_regex_pattern(text: str, match_underscore: bool, case_insensitive_first_char: bool, expected: str):
  rx = bot.prepare_regex_pattern(text, match_underscore, case_insensitive_first_char)
  assert(rx.pattern == expected)


def test_edit_synth_song_page_category():
  page_contents = """{{SingerCategory
|image =洛天依AI.jpg
|voicesynth =ACE Virtual Singer
|name =Luo Tianyi
|origname =洛天依
|language =Mandarin Chinese
|illustrator = [[ideolo]]
|developer =Shanghai HENIAN Information Technology Co. Ltd. and timedomAIn
|releasedate = August 27, 2022 (public beta)
|voiceprovider =Shan Xin
|readmore =https://vocadb.net/Ar/76197
|sitename =Vocaloid Database
|characterdisambig =1
|other =}}"""
  got = bot.edit_synth_song_page_category(
    page_contents=page_contents, 
    old_engine="ACE Virtual Singer",
    new_engine="Foo Studio"
  )
  expected = """{{SingerCategory
|image =洛天依AI.jpg
|voicesynth = Foo Studio
|name =Luo Tianyi
|origname =洛天依
|language =Mandarin Chinese
|illustrator = [[ideolo]]
|developer =Shanghai HENIAN Information Technology Co. Ltd. and timedomAIn
|releasedate = August 27, 2022 (public beta)
|voiceprovider =Shan Xin
|readmore =https://vocadb.net/Ar/76197
|sitename =Vocaloid Database
|characterdisambig =1
|other =}}"""
  assert(got == expected)

def test_edit_synth_album_page_category():
  page_contents = """{{AlbumCat|Luo Tianyi|ACE Virtual Singer}}"""
  got = bot.edit_synth_album_page_category(
    page_contents=page_contents,
    old_engine="ACE Virtual Singer",
    new_engine="Foo Studio"
  )
  expected = """{{AlbumCat|Luo Tianyi|Foo Studio}}"""
  assert(got == expected)

@pytest.mark.parametrize(
  "text, expected",
  [
    ("[[Luo Tianyi (ACE Virtual Singer)]]", "[[Luo Tianyi (Foo Studio)]]"),
    ("[[Xingchen (VOCALOID)]]", "[[Xingchen (VOCALOID)]]"),
    ("[[Luo Tianyi (VOCALOID)]]", "[[Luo Tianyi (VOCALOID)]]"),
    ("[[Luo Tianyi (ACE Virtual Singer)|Luo Heng]]", "[[Luo Tianyi (Foo Studio)|Luo Heng]]"),
    ("[[Xingchen (VOCALOID)|Stardust]]", "[[Xingchen (VOCALOID)|Stardust]]"),
    ("[[Luo Tianyi (ACE Virtual Singer)]] [[Xingchen (VOCALOID)]]", "[[Luo Tianyi (Foo Studio)]] [[Xingchen (VOCALOID)]]"),
    ("[[Luo  Tianyi (ACE Virtual Singer)]]", "[[Luo Tianyi (Foo Studio)]]"),
  ]
)
def test_edit_internal_links_of_synth(text: str, expected: str):
  got = bot._edit_internal_links_of_synth(
    text, 
    old_engine="ACE Virtual Singer", 
    new_engine="Foo Studio", 
    disambiguated_synths=set(["Luo Tianyi"])
  )
  assert(got == expected)

@pytest.mark.parametrize(
  "page_contents, expected",
  [
    (
      """{{sort}}{{Infobox Song
|songtitle = "'''别看我'''"<br />Traditional Chinese: 別看我<br />Pinyin: Bié Kàn Wǒ<br />English: Don't Look at Me
|color = #424960; color:white
|original upload date = {{Date|2023|August|25}}
|singer = [[Luo Tianyi (ACE Virtual Singer)]]
|producer = [[Cidai Jun]] (music, lyrics)<br />[[Creuzer (tuner)|Creuzer]] (tuning)<br />[[Tianbaizai]] (PV)<br />长戟大兜虫 (illustration)<br />Agaii, [[Evalia]] (PV materials)
|#views = 36,000+
|link = {{#|https://www.bilibili.com/video/BV1uu4y1D75k/}}
|language = Mandarin
}}

==Lyrics==
{{lyrics toggle|cn:Mandarin|py:Pinyin|eng:English}}
{| {{lyrics table class}}
|- class="lyrics-table-header"
! {{lyrics header}}
|-
|FOO
|BAR
|}

[[Category:Cidai Jun songs list]]
[[Category:Creuzer songs list/Tuning]]
[[Category:Tianbaizai songs list/Visuals]]
[[Category:Evalia songs list/Visuals]]""", 
      """{{sort}}{{Infobox Song
|songtitle = "'''别看我'''"<br />Traditional Chinese: 別看我<br />Pinyin: Bié Kàn Wǒ<br />English: Don't Look at Me
|color = #424960; color:white
|original upload date = {{Date|2023|August|25}}
|singer = [[Luo Tianyi (Foo Studio)]]
|producer = [[Cidai Jun]] (music, lyrics)<br />[[Creuzer (tuner)|Creuzer]] (tuning)<br />[[Tianbaizai]] (PV)<br />长戟大兜虫 (illustration)<br />Agaii, [[Evalia]] (PV materials)
|#views = 36,000+
|link = {{#|https://www.bilibili.com/video/BV1uu4y1D75k/}}
|language = Mandarin
}}

==Lyrics==
{{lyrics toggle|cn:Mandarin|py:Pinyin|eng:English}}
{| {{lyrics table class}}
|- class="lyrics-table-header"
! {{lyrics header}}
|-
|FOO
|BAR
|}

[[Category:Cidai Jun songs list]]
[[Category:Creuzer songs list/Tuning]]
[[Category:Tianbaizai songs list/Visuals]]
[[Category:Evalia songs list/Visuals]]"""
    ),
    (
      """{{sort}}{{Infobox Song
|songtitle = "'''别看我'''"<br />Traditional Chinese: 別看我<br />Pinyin: Bié Kàn Wǒ<br />English: Don't Look at Me
|color = #424960; color:white
|original upload date = {{Date|2023|August|25}}
|singer = [[Luo Tianyi (ACE Virtual Singer)]] and [[Yuezheng Ling (ACE Virtual Singer)]]
|producer = [[Cidai Jun]] (music, lyrics)<br />[[Creuzer (tuner)|Creuzer]] (tuning)<br />[[Tianbaizai]] (PV)<br />长戟大兜虫 (illustration)<br />Agaii, [[Evalia]] (PV materials)
|#views = 36,000+
|link = {{#|https://www.bilibili.com/video/BV1uu4y1D75k/}}
|language = Mandarin
}}

==Lyrics==
{{lyrics toggle|cn:Mandarin|py:Pinyin|eng:English}}
{| {{lyrics table class}}
|- class="lyrics-table-header"
! {{lyrics header}}
|-
|FOO
|BAR
|}

[[Category:Cidai Jun songs list]]
[[Category:Creuzer songs list/Tuning]]
[[Category:Tianbaizai songs list/Visuals]]
[[Category:Evalia songs list/Visuals]]""", 
      """{{sort}}{{Infobox Song
|songtitle = "'''别看我'''"<br />Traditional Chinese: 別看我<br />Pinyin: Bié Kàn Wǒ<br />English: Don't Look at Me
|color = #424960; color:white
|original upload date = {{Date|2023|August|25}}
|singer = [[Luo Tianyi (Foo Studio)]] and [[Yuezheng Ling (Foo Studio)]]
|producer = [[Cidai Jun]] (music, lyrics)<br />[[Creuzer (tuner)|Creuzer]] (tuning)<br />[[Tianbaizai]] (PV)<br />长戟大兜虫 (illustration)<br />Agaii, [[Evalia]] (PV materials)
|#views = 36,000+
|link = {{#|https://www.bilibili.com/video/BV1uu4y1D75k/}}
|language = Mandarin
}}

==Lyrics==
{{lyrics toggle|cn:Mandarin|py:Pinyin|eng:English}}
{| {{lyrics table class}}
|- class="lyrics-table-header"
! {{lyrics header}}
|-
|FOO
|BAR
|}

[[Category:Cidai Jun songs list]]
[[Category:Creuzer songs list/Tuning]]
[[Category:Tianbaizai songs list/Visuals]]
[[Category:Evalia songs list/Visuals]]"""
    ),
    (
      """{{sort}}{{Infobox Song
|songtitle = "'''别看我'''"<br />Traditional Chinese: 別看我<br />Pinyin: Bié Kàn Wǒ<br />English: Don't Look at Me
|color = #424960; color:white
|original upload date = {{Date|2023|August|25}}
|singer = [[Luo Tianyi (ACE Virtual Singer)]] and [[Xingchen (VOCALOID)]]
|producer = [[Cidai Jun]] (music, lyrics)<br />[[Creuzer (tuner)|Creuzer]] (tuning)<br />[[Tianbaizai]] (PV)<br />长戟大兜虫 (illustration)<br />Agaii, [[Evalia]] (PV materials)
|#views = 36,000+
|link = {{#|https://www.bilibili.com/video/BV1uu4y1D75k/}}
|language = Mandarin
}}

==Lyrics==
{{lyrics toggle|cn:Mandarin|py:Pinyin|eng:English}}
{| {{lyrics table class}}
|- class="lyrics-table-header"
! {{lyrics header}}
|-
|FOO
|BAR
|}

[[Category:Cidai Jun songs list]]
[[Category:Creuzer songs list/Tuning]]
[[Category:Tianbaizai songs list/Visuals]]
[[Category:Evalia songs list/Visuals]]""", 
      """{{sort}}{{Infobox Song
|songtitle = "'''别看我'''"<br />Traditional Chinese: 別看我<br />Pinyin: Bié Kàn Wǒ<br />English: Don't Look at Me
|color = #424960; color:white
|original upload date = {{Date|2023|August|25}}
|singer = [[Luo Tianyi (Foo Studio)]] and [[Xingchen (VOCALOID)]]
|producer = [[Cidai Jun]] (music, lyrics)<br />[[Creuzer (tuner)|Creuzer]] (tuning)<br />[[Tianbaizai]] (PV)<br />长戟大兜虫 (illustration)<br />Agaii, [[Evalia]] (PV materials)
|#views = 36,000+
|link = {{#|https://www.bilibili.com/video/BV1uu4y1D75k/}}
|language = Mandarin
}}

==Lyrics==
{{lyrics toggle|cn:Mandarin|py:Pinyin|eng:English}}
{| {{lyrics table class}}
|- class="lyrics-table-header"
! {{lyrics header}}
|-
|FOO
|BAR
|}

[[Category:Cidai Jun songs list]]
[[Category:Creuzer songs list/Tuning]]
[[Category:Tianbaizai songs list/Visuals]]
[[Category:Evalia songs list/Visuals]]"""
    ),
    (
      """{{sort}}{{Infobox Song
|songtitle = "'''别看我'''"<br />Traditional Chinese: 別看我<br />Pinyin: Bié Kàn Wǒ<br />English: Don't Look at Me
|color = #424960; color:white
|original upload date = {{Date|2023|August|25}}
|singer = [[Luo Tianyi (ACE Virtual Singer)]] and [[Chang Ge]]
|producer = [[Cidai Jun]] (music, lyrics)<br />[[Creuzer (tuner)|Creuzer]] (tuning)<br />[[Tianbaizai]] (PV)<br />长戟大兜虫 (illustration)<br />Agaii, [[Evalia]] (PV materials)
|#views = 36,000+
|link = {{#|https://www.bilibili.com/video/BV1uu4y1D75k/}}
|language = Mandarin
}}

==Lyrics==
{{lyrics toggle|cn:Mandarin|py:Pinyin|eng:English}}
{| {{lyrics table class}}
|- class="lyrics-table-header"
! {{lyrics header}}
|-
|FOO
|BAR
|}

[[Category:Cidai Jun songs list]]
[[Category:Creuzer songs list/Tuning]]
[[Category:Tianbaizai songs list/Visuals]]
[[Category:Evalia songs list/Visuals]]""", 
      """{{sort}}{{Infobox Song
|songtitle = "'''别看我'''"<br />Traditional Chinese: 別看我<br />Pinyin: Bié Kàn Wǒ<br />English: Don't Look at Me
|color = #424960; color:white
|original upload date = {{Date|2023|August|25}}
|singer = [[Luo Tianyi (Foo Studio)]] and [[Chang Ge]]
|producer = [[Cidai Jun]] (music, lyrics)<br />[[Creuzer (tuner)|Creuzer]] (tuning)<br />[[Tianbaizai]] (PV)<br />长戟大兜虫 (illustration)<br />Agaii, [[Evalia]] (PV materials)
|#views = 36,000+
|link = {{#|https://www.bilibili.com/video/BV1uu4y1D75k/}}
|language = Mandarin
}}

==Lyrics==
{{lyrics toggle|cn:Mandarin|py:Pinyin|eng:English}}
{| {{lyrics table class}}
|- class="lyrics-table-header"
! {{lyrics header}}
|-
|FOO
|BAR
|}

[[Category:Cidai Jun songs list]]
[[Category:Creuzer songs list/Tuning]]
[[Category:Tianbaizai songs list/Visuals]]
[[Category:Evalia songs list/Visuals]]"""
    ),
    (
      """{{sort}}{{Infobox Song
|songtitle = "'''别看我'''"<br />Traditional Chinese: 別看我<br />Pinyin: Bié Kàn Wǒ<br />English: Don't Look at Me
|color = #424960; color:white
|original upload date = {{Date|2023|August|25}}
|singer = Luo Tianyi <small>([[Luo Tianyi (VOCALOID)|VOCALOID]] and [[Luo Tianyi (ACE Virtual Singer)|ACE Virtual Singer]])</small>
|producer = [[Cidai Jun]] (music, lyrics)<br />[[Creuzer (tuner)|Creuzer]] (tuning)<br />[[Tianbaizai]] (PV)<br />长戟大兜虫 (illustration)<br />Agaii, [[Evalia]] (PV materials)
|#views = 36,000+
|link = {{#|https://www.bilibili.com/video/BV1uu4y1D75k/}}
|language = Mandarin
}}

==Lyrics==
{{lyrics toggle|cn:Mandarin|py:Pinyin|eng:English}}
{| {{lyrics table class}}
|- class="lyrics-table-header"
! {{lyrics header}}
|-
|FOO
|BAR
|}

[[Category:Cidai Jun songs list]]
[[Category:Creuzer songs list/Tuning]]
[[Category:Tianbaizai songs list/Visuals]]
[[Category:Evalia songs list/Visuals]]""", 
      """{{sort}}{{Infobox Song
|songtitle = "'''别看我'''"<br />Traditional Chinese: 別看我<br />Pinyin: Bié Kàn Wǒ<br />English: Don't Look at Me
|color = #424960; color:white
|original upload date = {{Date|2023|August|25}}
|singer = Luo Tianyi <small>([[Luo Tianyi (VOCALOID)|VOCALOID]] and [[Luo Tianyi (Foo Studio)|ACE Virtual Singer]])</small>
|producer = [[Cidai Jun]] (music, lyrics)<br />[[Creuzer (tuner)|Creuzer]] (tuning)<br />[[Tianbaizai]] (PV)<br />长戟大兜虫 (illustration)<br />Agaii, [[Evalia]] (PV materials)
|#views = 36,000+
|link = {{#|https://www.bilibili.com/video/BV1uu4y1D75k/}}
|language = Mandarin
}}

==Lyrics==
{{lyrics toggle|cn:Mandarin|py:Pinyin|eng:English}}
{| {{lyrics table class}}
|- class="lyrics-table-header"
! {{lyrics header}}
|-
|FOO
|BAR
|}

[[Category:Cidai Jun songs list]]
[[Category:Creuzer songs list/Tuning]]
[[Category:Tianbaizai songs list/Visuals]]
[[Category:Evalia songs list/Visuals]]"""
    ),
  ]
)
def test_edit_song_page(page_contents: str, expected: str):
  got = bot.edit_song_page(
    page_contents=page_contents,
    old_engine="ACE Virtual Singer",
    new_engine="Foo Studio",
    disambiguated_synths=set(["Luo Tianyi", "Yuezheng Ling"])
  )
  assert(got == expected)

@pytest.mark.parametrize(
  "page_contents, expected",
  [
    ("""{{Album Infobox
|title = Wànhuá Yī Huì
|orgtitle = 万华依绘
|label = Shanghai HENIAN Information Technology Co. Ltd. and StreetVoice Taiwan
|desc = an album featuring several producers
|date = {{DateAlbum|2023|August|24}}
|vdb = 37909
|compilation = 1
|sp-embed = 4Zngwur85QXNkpqYKi6d4d
|yt-playlist = OLAK5uy_nJlxmr3KRoO-Z6fpY2y4N3p8BA6wtL-Z0

|color = #232C71; color:white
|tr1 = [[茉莉花 (Mo Li Hua)]]
|tr1s = [[Producer]] ft. [[Luo Tianyi (ACE Virtual Singer)|Luo Tianyi]]
|tr2 = [[茉莉花 (Mo Li Hua 2)]]
|tr2s = [[Producer]] ft. [[Xingchen (VOCALOID)|Xingchen]]
|tr3 = [[茉莉花 (Mo Li Hua 3)]]
|tr3s = [[Producer]] ft. [[Yuezheng Ling (ACE Virtual Singer)|Yuezheng Ling]]
}}

[[Category:Albums featuring ACE Virtual Singer]]
[[Category:Albums featuring VOCALOID]]
[[Category:Albums featuring Luo Tianyi (ACE Virtual Singer)]]
[[Category:Albums featuring Xingchen (VOCALOID)]]
[[Category:Albums featuring Yuezheng Ling (ACE Virtual Singer)]]
[[Category:Producer songs list/Albums]]""", 
    """{{Album Infobox
|title = Wànhuá Yī Huì
|orgtitle = 万华依绘
|label = Shanghai HENIAN Information Technology Co. Ltd. and StreetVoice Taiwan
|desc = an album featuring several producers
|date = {{DateAlbum|2023|August|24}}
|vdb = 37909
|compilation = 1
|sp-embed = 4Zngwur85QXNkpqYKi6d4d
|yt-playlist = OLAK5uy_nJlxmr3KRoO-Z6fpY2y4N3p8BA6wtL-Z0

|color = #232C71; color:white
|tr1 = [[茉莉花 (Mo Li Hua)]]
|tr1s = [[Producer]] ft. [[Luo Tianyi (Foo Studio)|Luo Tianyi]]
|tr2 = [[茉莉花 (Mo Li Hua 2)]]
|tr2s = [[Producer]] ft. [[Xingchen (VOCALOID)|Xingchen]]
|tr3 = [[茉莉花 (Mo Li Hua 3)]]
|tr3s = [[Producer]] ft. [[Yuezheng Ling (Foo Studio)|Yuezheng Ling]]
}}

[[Category:Albums featuring Foo Studio]]
[[Category:Albums featuring VOCALOID]]
[[Category:Albums featuring Luo Tianyi (Foo Studio)]]
[[Category:Albums featuring Xingchen (VOCALOID)]]
[[Category:Albums featuring Yuezheng Ling (Foo Studio)]]
[[Category:Producer songs list/Albums]]""")
  ]
)
def test_edit_album_page(page_contents: str, expected: str):
  got = bot.edit_album_page(
    page_contents=page_contents,
    old_engine="ACE Virtual Singer",
    new_engine="Foo Studio",
    disambiguated_synths=set(["Luo Tianyi", "Yuezheng Ling"])
  )
  assert(got == expected)

@pytest.mark.parametrize(
  "page_contents, expected",
  [
    ("""<div class="producer-links">
[[File:AnnyJuly.jpg|250px|center]]
==Producer categories==
{{ProdLinks|AnnyJuly|valid}}

==External Links==
* Missevan: [https://www.missevan.com/4166918/]
* Lofter: [https://annyjuly.lofter.com/]

===Media===
* [http://space.bilibili.com/333835/#!/index Bilibili]
* [https://www.youtube.com/@annyjuly6521 YouTube]
* [http://5sing.kugou.com/73216851/default.html 5Sing]
* [https://music.163.com/#/artist?id=29029316 NetEase Music]

===Unofficial===
{{links |p=yes
   |atmiku = 
   |atutau = 
   |nico   = 
   |vocadb = 54767
   |tag    = 
   |mgp    = 
}}
</div>

'''AnnyJuly''' is a vocal synth producer who makes mostly Mandarin songs. They use a variety of different voicebank types, including VOCALOID, UTAU, and NIAONiao. They occasionally produce English original songs.

==Works==
{| class="sortable producer-table"
|- class="vcolor-default"
! {{pwt head}}
|-
| {{pwt row|FOO}}
|}

__NOTOC__
[[Category:Producers]]
[[Category:Composers]]
[[Category:Lyricists]]
[[Category:Mandarin original producers]]
[[Category:Producers using VOCALOID]]
[[Category:Producers using NIAONiao]]
[[Category:Producers using UTAU]]
[[Category:Producers using Synthesizer V]]
[[Category:Producers using X Studio Singer]]
[[Category:Producers using DeepVocal]]
[[Category:Producers using MUTA]]
[[Category:Producers using AISingers]]
[[Category:Producers using Sharpkey]]
[[Category:Producers using VocalSharp]]
[[Category:Producers using ACE Virtual Singer]]
[[Category:Animators]]
[[Category:Arrangers]]""", """<div class="producer-links">
[[File:AnnyJuly.jpg|250px|center]]
==Producer categories==
{{ProdLinks|AnnyJuly|valid}}

==External Links==
* Missevan: [https://www.missevan.com/4166918/]
* Lofter: [https://annyjuly.lofter.com/]

===Media===
* [http://space.bilibili.com/333835/#!/index Bilibili]
* [https://www.youtube.com/@annyjuly6521 YouTube]
* [http://5sing.kugou.com/73216851/default.html 5Sing]
* [https://music.163.com/#/artist?id=29029316 NetEase Music]

===Unofficial===
{{links |p=yes
   |atmiku = 
   |atutau = 
   |nico   = 
   |vocadb = 54767
   |tag    = 
   |mgp    = 
}}
</div>

'''AnnyJuly''' is a vocal synth producer who makes mostly Mandarin songs. They use a variety of different voicebank types, including VOCALOID, UTAU, and NIAONiao. They occasionally produce English original songs.

==Works==
{| class="sortable producer-table"
|- class="vcolor-default"
! {{pwt head}}
|-
| {{pwt row|FOO}}
|}

__NOTOC__
[[Category:Producers]]
[[Category:Composers]]
[[Category:Lyricists]]
[[Category:Mandarin original producers]]
[[Category:Producers using VOCALOID]]
[[Category:Producers using NIAONiao]]
[[Category:Producers using UTAU]]
[[Category:Producers using Synthesizer V]]
[[Category:Producers using X Studio Singer]]
[[Category:Producers using DeepVocal]]
[[Category:Producers using MUTA]]
[[Category:Producers using AISingers]]
[[Category:Producers using Sharpkey]]
[[Category:Producers using VocalSharp]]
[[Category:Producers using Foo Studio]]
[[Category:Animators]]
[[Category:Arrangers]]""")
  ]
)
def test_edit_producer_page(page_contents: str, expected: str):
  got = bot.edit_producer_page(
    page_contents=page_contents,
    old_engine="ACE Virtual Singer",
    new_engine="Foo Studio",
    disambiguated_synths=set(["Luo Tianyi", "Yuezheng Ling"])
  )
  assert(got == expected)