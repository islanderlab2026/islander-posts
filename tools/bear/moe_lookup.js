// 教育部《重編國語辭典修訂本》批次查詢（2026-11-15 同意）
// 用法：Chrome 開 https://dict.revised.moe.edu.tw/ 任一頁，把 W 換成要查的詞，用 javascript_tool 執行
// 回傳每個詞：注音｜漢語拼音｜第一段釋義（查不到會寫「查無」→ 不能用）
const W = ['詞一', '詞二'];
const out = [];
for (const w of W) {
  try {
    const t = await (await fetch('/search.jsp?md=1&word=' + encodeURIComponent(w))).text();
    let doc = new DOMParser().parseFromString(t, 'text/html');
    let art = doc.querySelector('article');
    if (!art) {
      const a = [...doc.querySelectorAll('a[href*="dictView"]')].find(a => a.innerText.replace(/\s/g, '') === w);
      if (a) { doc = new DOMParser().parseFromString(await (await fetch(a.getAttribute('href'))).text(), 'text/html'); art = doc.querySelector('article'); }
    }
    const txt = art ? art.innerText.replace(/\s+/g, ' ') : '';
    const zy = (txt.match(/注 音 ([ㄅ-ㄩˊˇˋ˙ ]+?) 漢語拼音/) || [, '查無'])[1];
    const py = (txt.match(/漢語拼音 ([a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü ]+?) (?:相 似|相 反|釋 義|部 首|異體)/) || [, '查無'])[1];
    const i = txt.indexOf('釋 義');
    out.push(`${w}｜${zy}｜${py}｜${i >= 0 ? txt.slice(i + 4, i + 70) : '查無'}`);
  } catch (e) { out.push(`${w}｜錯誤 ${e}`); }
}
out.join('\n');
