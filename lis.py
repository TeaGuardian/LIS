import pymorphy2
import sqlite3
morph = pymorphy2.MorphAnalyzer()


def limited_text_split(lsmax, text, splittor=" ", ignos=" "):
    trf, lp, ste = lsmax // 2, 0, 0
    if lsmax < 8:
        print("too small")
    rez, line = [], ""
    for si in text:
        if si == ignos and ste == 0:
            continue
        if si == splittor:
            lp = ste
        if len(line) >= lsmax:
            if ste - lp > trf or ste - lp == 0:
                rez.append(line)
                line, ste, lp = "", -1, 0
            else:
                rez.append(line[:lp])
                line += si
                line, ste, lp = line[lp + 1:], len(line[lp + 1:]) - 1, 0
        else:
            line += si
        ste += 1
    if line:
        rez.append(line)
    return rez


def distance(a, b):
    n, m = len(a), len(b)
    if n > m:
        a, b = b, a
        n, m = m, n
    current_row = range(n + 1)
    for i in range(1, m + 1):
        previous_row, current_row = current_row, [i] + [0] * n
        for j in range(1, n + 1):
            add, delete, change = previous_row[j] + 1, current_row[j - 1] + 1, previous_row[j - 1]
            if a[j - 1] != b[i - 1]:
                change += 1
            current_row[j] = min(add, delete, change)
    return current_row[n]


class Morpher:
    deparlist = {"NOUN": "существительное", "ADJF": "прилагательное (полное)", "ADJS": "прилагательное (краткое)",
                 "COMP": "компаратив", "VERB": "глагол (личная форма)", "INFN": "глагол (инфинитив)",
                 "PRTF": "причастие (полное)", "PRTS": "причастие (краткое)", "GRND": "деепричастие",
                 "NUMR": "числительное", "ADVB": "наречие", "NPRO": "местоимение-существительное",
                 "PRED": "предикатив", "PREP": "предлог", "CONJ": "союз", "PRCL": "частица", "INTJ": "междометие",
                 "LATN": "a russian", "PNCT": "?!", "NUMB": "228 / 2.28", "intg": "228", "real": "2.28", "ROMN": "X", "UNKN": "WTF?!"}
    morlist = [("NOUN", "ADJF"), ("NOUN", "ADJS"), ("NOUN", "NUMR"), ("NOUN", "NOUN"), ("VERB", "NOUN"),
               ("VERB", "ADVB"), ("VERB", "INFN"), ("NOUN", "PRTF"), ("INFN", "ADVB"), ("VERB", "ADJS")]
    nw1, nw2 = None, None

    def __init__(self):
        self.con = sqlite3.connect("model_1.db")
        self.cur = self.con.cursor()
        self.ind = len(self.cur.execute(f"""SELECT main_tag, second_tag from tags""").fetchall())
        self.cur.execute("""CREATE TABLE IF NOT EXISTS words(
                        main_word TEXT,
                        main_tag TEXT,
                        second_word TEXT,
                        second_tag TEXT,
                        usr TEXT);
                        """)
        self.cur.execute("""CREATE TABLE IF NOT EXISTS tags(
                        main_tag TEXT,
                        second_tag TEXT);
                        """)
        self.con.commit()
        print(f"morpheme class inited\nwords: {self.ind}")

    def is_pare(self, wo1, wo2):
        p1, p2 = morph.parse(wo1)[0], morph.parse(wo2)[0]
        t1, t2 = p1.tag.__str__(), p2.tag.__str__()
        data = self.cur.execute(f"""SELECT main_tag, second_tag from tags where main_tag == '{t1}' and second_tag == '{t2}'""").fetchall()
        return len(data) > 0

    def sub_index(self, word1, word2, usr):
        global morph
        p1 = morph.parse(word1)[0]
        p2 = morph.parse(word2)[0]
        if (p1.tag.POS, p2.tag.POS) not in self.morlist:
            p1, p2 = p2, p1
            word1, word2 = word2, word1
        ref_an = f"main: {word1}; {p1.tag.__str__()}; {self.deparlist[p1.tag.POS]}\nsecond: {word2}; {p2.tag.__str__()}; {self.deparlist[p2.tag.POS]}"
        if (p1.tag.POS, p2.tag.POS) not in self.morlist:
            mes = f"status: !error! части речи не сочетаются\n" + ref_an
            return -1, mes
        return self.test_on_index(word1, word2, p1.tag.__str__(), p2.tag.__str__(), ref_an, usr)

    def test_on_index(self, w1, w2, t1, t2, mes, usr):
        data = self.cur.execute(f"""SELECT main_tag, second_tag from tags where main_tag == '{t1}' and second_tag == '{t2}'""").fetchall()
        if data:
            return 0, "status: уже существует подобное сочетание\n" + mes
        self.cur.execute(f"""INSERT INTO words(main_word, main_tag, second_word, second_tag, usr) 
                         VALUES('{w1}', '{t1}', '{w2}', '{t2}', '{usr}');""")
        self.cur.execute(f"""INSERT INTO tags(main_tag, second_tag) 
                         VALUES('{t1}', '{t2}');""")
        self.con.commit()
        self.ind += 1
        return 1, "status: nice work, bro\n" + mes + f"\nwords: {self.ind}"

    def off(self):
        self.con.close()

    def get_words(self, wl):
        pares, adp, pares_l = {}, {}, []
        for i, wo1 in enumerate(wl):
            for j, wo2 in enumerate(wl):
                if i != j and self.is_pare(wo1, wo2):
                    if wo1 not in pares.keys():
                        pares[wo1] = []
                    pares[wo1].append(wo2)
                    pares_l.append(wo1 + " - " + wo2)
        return pares, pares_l

    def delite_phrase(self, word1, word2):
        global morph
        p1 = morph.parse(word1)[0]
        p2 = morph.parse(word2)[0]
        if (p1.tag.POS, p2.tag.POS) not in self.morlist:
            p1, p2 = p2, p1
        t1, t2 = p1.tag.__str__(), p2.tag.__str__()
        data1 = self.cur.execute(f"""SELECT main_tag from tags where main_tag == '{t1}' and second_tag == '{t2}'""").fetchall()
        self.cur.execute(f"""DELETE from words where main_tag == '{t1}' and second_tag == '{t2}'""")
        self.cur.execute(f"""DELETE from tags where main_tag == '{t1}' and second_tag == '{t2}'""")
        data2 = self.cur.execute(f"""SELECT main_tag from tags where main_tag == '{t1}' and second_tag == '{t2}'""").fetchall()
        if len(data1) == 1 and len(data2) == 0:
            self.con.commit()
            return "successful"
        return "!!!"

    def all_data(self):
        data = self.cur.execute(f"""SELECT main_tag, main_word, second_tag, second_word from words""").fetchall()
        print(">>2")
        return "\n".join(["-".join(list(i)) for i in data])


if __name__ == "__main__":
    mor = Morpher()
    print(mor.get_words("у него были жёсткие жёлтые волосы и крутая синяя куртка а ещё он был силён и крепок и жил хорошо".split()))
    # print(mor.sub_index("жил", "хорошо", "sempai"))