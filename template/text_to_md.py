import sys,re
# usage: text_to_md.py email_text_path out_md_path
# Rebuilds the edition markdown from the plain-text email (the inverse of md_to_email_text.py).
src,out=sys.argv[1:3]
lines=open(src).read().splitlines()
i=0
while i<len(lines) and not lines[i].startswith('====='): i+=1
body=lines[i+1:]
O=["# Terms Undisclosed: Bay Blend","","Designed by hand, assembled by machine.",""]
sec=''
sec_first=False
NOSTAND={'THE LEAD','THREE THINGS TO BRING UP TODAY','THE ONE THING'}
def put(x):
    O.append(x)
k=0
while k<len(body):
    s=body[k].rstrip(); k+=1
    if not s.strip(): continue
    if s.startswith('Informed, opinionated, occasionally wrong'): break
    if sec_first and sec not in NOSTAND and not s.startswith(('  ','[')) and not re.match(r'^\d\. ',s) and k<len(body) and not body[k].strip():
        O.append('~ '+s); O.append(""); sec_first=False; continue
    sec_first=False
    if k<len(body) and re.fullmatch(r'-{3,}',body[k].strip()) and not s.startswith(' '):
        sec=s.strip(); k+=1
        if O[-1]!="": O.append("")
        O.append('## '+sec); O.append(""); sec_first=True; continue
    if s.startswith('  '):
        t=s.strip()
        lab,_,rest=t.partition(': ')
        rest=', '.join(re.sub(r'^(.+) \((https?://[^)]+)\)$',r'[\1](\2)',p) for p in re.split(r'(?<=\)), ',rest))
        O.append('> '+lab+': '+rest); O.append(""); continue
    m=re.match(r'^\[(UP|DOWN)\] (.*?\.) (.*)$',s)
    if m:
        O.append(f'**{m.group(1)}: {m.group(2)}** {m.group(3)}'); O.append(""); continue
    if re.match(r'^\d\. ',s):
        O.append(s)
        # keep numbered items adjacent
        continue
    s=re.sub(r'\(Source: (.+?) \((https?://[^)]+)\)\)',r'(Source: [\1](\2))',s)
    O.append(s); O.append("")
while O and O[-1]=="": O.pop()
open(out,'w').write("\n".join(O)+"\n")
