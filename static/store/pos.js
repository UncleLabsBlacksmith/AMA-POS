/* ============================================================
   สคริปต์หลักของระบบขายหน้าร้าน (เวอร์ชัน Tailwind)
   ส่วนที่ 1: ของใช้ร่วมทุกหน้า (ขนาดตัวหนังสือ / เสียงพูด / นาฬิกา)
   ส่วนที่ 2: หน้าขาย (ตะกร้า คิดเงินทอน บันทึกบิล)
   ============================================================ */

/* ---------------- ส่วนที่ 1 : ของใช้ร่วม ---------------- */

/* ขนาดตัวหนังสือฐาน (px) — Tailwind วัดทุกอย่างเป็น rem
   พอฐานใหญ่ขึ้น ปุ่ม ระยะห่าง และตัวหนังสือจะใหญ่ขึ้นตามกันทั้งหน้า */
const FONT_STEPS = [21, 24, 27, 30];

function applyFont(px) {
  document.documentElement.style.setProperty('--pos-font', px + 'px');
  localStorage.setItem('pos_font', px);
}

function initFont() {
  const saved = parseInt(localStorage.getItem('pos_font') || '21', 10);
  applyFont(FONT_STEPS.includes(saved) ? saved : 21);
  const btn = document.getElementById('fontBtn');
  if (!btn) return;
  btn.addEventListener('click', () => {
    const now = parseInt(localStorage.getItem('pos_font') || '21', 10);
    const next = FONT_STEPS[(FONT_STEPS.indexOf(now) + 1) % FONT_STEPS.length];
    applyFont(next);
    say('ตัวหนังสือขนาด ' + (FONT_STEPS.indexOf(next) + 1));
  });
}

/* --- เสียงพูดภาษาไทย ช่วยให้ไม่ต้องเพ่งอ่านตัวเลข --- */
let voiceOn = localStorage.getItem('pos_voice') !== 'off';

function say(text) {
  if (!voiceOn || !('speechSynthesis' in window)) return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'th-TH';
    u.rate = 0.92;   // พูดช้าลงเล็กน้อย ฟังง่ายขึ้น
    u.volume = 1;
    window.speechSynthesis.speak(u);
  } catch (e) { /* เครื่องไม่รองรับก็ข้ามไป */ }
}

function initVoice() {
  const btn = document.getElementById('voiceBtn');
  if (!btn) return;
  const paint = () => {
    btn.textContent = voiceOn ? '🔊 เสียงเปิด' : '🔇 เสียงปิด';
    btn.classList.toggle('navbtn-on', voiceOn);
  };
  paint();
  btn.addEventListener('click', () => {
    voiceOn = !voiceOn;
    localStorage.setItem('pos_voice', voiceOn ? 'on' : 'off');
    paint();
    if (voiceOn) say('เปิดเสียงแล้ว');
  });
}

function initClock() {
  const el = document.getElementById('clock');
  if (!el) return;
  const tick = () => {
    const d = new Date();
    el.textContent = d.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' });
  };
  tick();
  setInterval(tick, 10000);
}

function baht(n) {
  return Number(n).toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function bahtWords(n) {
  const v = Math.round(Number(n) * 100) / 100;
  const i = Math.floor(v);
  const s = Math.round((v - i) * 100);
  return s === 0 ? `${i} บาท` : `${i} บาท ${s} สตางค์`;
}

function csrf() {
  const m = document.cookie.match(/csrftoken=([^;]+)/);
  return m ? m[1] : '';
}

/* ---------------- ส่วนที่ 2 : หน้าขาย ---------------- */

/* คลาส Tailwind ของกล่องเงินทอน แยกตามสถานะ เพื่อให้สลับสีได้ชัดเจน */
const CHANGE_STATES = {
  idle:  { box: ['bg-white', 'border-line'], value: [] },
  ok:    { box: ['bg-green-50', 'border-green-700'], value: ['text-green-700'] },
  short: { box: ['bg-red-50', 'border-red-700'], value: ['text-red-700'] },
};

function initPOS() {
  const grid = document.getElementById('grid');
  if (!grid) return;

  const PRODUCTS = JSON.parse(document.getElementById('productData').textContent);
  const byId = new Map(PRODUCTS.map(p => [p.id, p]));

  let cart = [];          // [{id, qty}]
  let paid = 0;           // เงินที่รับมา
  let method = 'cash';
  let activeCat = 'fav';

  const $ = id => document.getElementById(id);

  const emptyBox = msg =>
    `<div class="px-4 py-8 text-center text-lg text-inksoft">${msg}</div>`;

  /* ----- วาดตารางสินค้า ----- */
  function renderGrid() {
    const q = ($('search').value || '').trim().toLowerCase();
    let list = PRODUCTS;

    if (q) {
      list = PRODUCTS.filter(p =>
        p.name.toLowerCase().includes(q) || (p.barcode && p.barcode.includes(q)));
    } else if (activeCat === 'fav') {
      list = PRODUCTS.filter(p => p.favorite);
      if (list.length === 0) list = PRODUCTS;
    } else if (activeCat !== 'all') {
      list = PRODUCTS.filter(p => String(p.category) === String(activeCat));
    }

    grid.innerHTML = '';
    if (list.length === 0) {
      grid.innerHTML = emptyBox('ไม่พบสินค้า ลองพิมพ์ใหม่อีกครั้ง');
      return;
    }

    for (const p of list) {
      const low = p.track_stock && p.stock <= 3;
      const out = p.track_stock && p.stock <= 0;

      const b = document.createElement('button');
      b.className = 'tile' + (p.favorite ? ' tile-pinned' : '') + (out ? ' opacity-45' : '');

      const face = p.image
        ? `<img src="${p.image}" alt="" class="w-16 h-16 object-cover rounded-xl">`
        : `<span class="text-5xl leading-none">${p.emoji || '🛒'}</span>`;

      const stockLine = p.track_stock
        ? `<span class="text-sm ${low ? 'font-extrabold text-red-700' : 'text-inksoft'}">
             ${out ? 'ของหมด' : 'เหลือ ' + p.stock + ' ' + p.unit}
           </span>`
        : '';

      b.innerHTML = `${face}
        <span class="text-base font-extrabold leading-tight">${p.name}</span>
        <span class="text-xl font-black text-green-700">${baht(p.price)}฿</span>
        ${stockLine}`;

      b.addEventListener('click', () => addItem(p.id));
      grid.appendChild(b);
    }
  }

  /* ----- ตะกร้า ----- */
  function addItem(id, n = 1) {
    const p = byId.get(id);
    if (!p) return;
    const row = cart.find(r => r.id === id);
    if (row) row.qty += n; else cart.push({ id, qty: n });
    say(`${p.name} ${bahtWords(p.price)}`);
    renderCart();
  }

  function setQty(id, n) {
    const row = cart.find(r => r.id === id);
    if (!row) return;
    row.qty = n;
    if (row.qty <= 0) cart = cart.filter(r => r.id !== id);
    renderCart();
  }

  function total() {
    return cart.reduce((s, r) => s + byId.get(r.id).price * r.qty, 0);
  }

  function renderCart() {
    const list = $('cartList');
    list.innerHTML = '';

    if (cart.length === 0) {
      list.innerHTML = emptyBox('ยังไม่มีสินค้า<br>กดที่รูปสินค้าทางซ้ายได้เลย');
    } else {
      for (const r of cart) {
        const p = byId.get(r.id);
        const el = document.createElement('div');
        el.className = 'px-1 py-2 border-b-2 border-stone-100';
        el.innerHTML = `
          <div class="flex items-start gap-2">
            <span class="text-3xl leading-none">${p.emoji || '🛒'}</span>
            <span class="grow min-w-0">
              <span class="block text-base font-extrabold leading-tight">${p.name}</span>
              <span class="block text-sm text-inksoft">${baht(p.price)}฿ / ${p.unit}</span>
            </span>
            <span class="text-xl font-black whitespace-nowrap">${baht(p.price * r.qty)}฿</span>
          </div>
          <div class="flex items-center gap-1 mt-1">
            <button class="qbtn" data-a="minus">−</button>
            <span class="min-w-11 text-center text-xl font-black">${r.qty}</span>
            <button class="qbtn" data-a="plus">+</button>
            <button class="qbtn qbtn-del ml-auto" data-a="del" title="เอาออก">🗑</button>
          </div>`;

        el.querySelectorAll('.qbtn').forEach(btn => {
          btn.addEventListener('click', () => {
            const a = btn.dataset.a;
            if (a === 'plus') setQty(r.id, r.qty + 1);
            else if (a === 'minus') setQty(r.id, r.qty - 1);
            else { setQty(r.id, 0); say('เอา ' + p.name + ' ออกแล้ว'); }
          });
        });
        list.appendChild(el);
      }
    }

    $('totalValue').textContent = baht(total()) + '฿';
    $('cartCount').textContent = cart.reduce((s, r) => s + r.qty, 0) + ' ชิ้น';
    renderChange();
    $('payBtn').disabled = cart.length === 0;
  }

  /* ----- เงินทอน ----- */
  function setChangeState(state) {
    const box = $('changeBox');
    const value = $('changeValue');
    for (const s of Object.values(CHANGE_STATES)) {
      box.classList.remove(...s.box);
      value.classList.remove(...s.value);
    }
    box.classList.add(...CHANGE_STATES[state].box);
    value.classList.add(...CHANGE_STATES[state].value);
  }

  function renderChange() {
    const t = total();
    if (method !== 'cash') {
      setChangeState('idle');
      $('paidValue').textContent = method === 'credit' ? 'ลงบัญชีไว้' : 'รับโอน';
      $('changeValue').textContent = '-';
      return;
    }
    $('paidValue').textContent = paid > 0 ? baht(paid) + '฿' : 'ยังไม่รับเงิน';
    if (paid <= 0 || cart.length === 0) {
      setChangeState('idle');
      $('changeValue').textContent = '-';
      return;
    }
    const diff = paid - t;
    setChangeState(diff >= 0 ? 'ok' : 'short');
    $('changeValue').textContent = (diff >= 0 ? '' : 'ขาด ') + baht(Math.abs(diff)) + '฿';
  }

  function addPaid(n) {
    paid += n;
    renderChange();
    say('รับมา ' + bahtWords(paid));
  }

  /* ----- บันทึกบิล ----- */
  async function checkout() {
    if (cart.length === 0) return;
    const t = total();
    if (method === 'credit' && !$('customerSelect').value) {
      alert('ซื้อเชื่อต้องเลือกชื่อลูกค้าก่อนนะคะ');
      say('กรุณาเลือกชื่อลูกค้าก่อน');
      return;
    }

    $('payBtn').disabled = true;
    try {
      const res = await fetch('/api/checkout/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
        body: JSON.stringify({
          items: cart,
          paid: method === 'cash' ? paid : t,
          payment_method: method,
          customer_id: $('customerSelect').value || null,
        }),
      });
      const data = await res.json();
      if (!data.ok) {
        alert(data.error || 'บันทึกไม่สำเร็จ');
        say(data.error || 'บันทึกไม่สำเร็จ');
        $('payBtn').disabled = false;
        return;
      }
      showDone(data);
    } catch (e) {
      alert('บันทึกไม่สำเร็จ ลองใหม่อีกครั้ง');
      $('payBtn').disabled = false;
    }
  }

  function showDone(data) {
    $('doneTotal').textContent = baht(data.total) + '฿';
    const hasChange = method === 'cash' && data.change > 0;
    $('doneChangeWrap').hidden = !hasChange;
    $('doneChange').textContent = baht(data.change) + '฿';
    $('doneBillLink').href = data.bill_url;
    $('doneMethod').textContent =
      method === 'credit' ? 'ลงบัญชีซื้อเชื่อเรียบร้อย'
        : method === 'transfer' ? 'รับโอนเรียบร้อย' : 'รับเงินสดเรียบร้อย';
    $('doneOverlay').hidden = false;

    if (hasChange) say('ทอน ' + bahtWords(data.change));
    else say('เก็บเงิน ' + bahtWords(data.total) + ' เรียบร้อย');
  }

  function clearAll() {
    cart = [];
    paid = 0;
    method = 'cash';
    $('customerSelect').value = '';
    $('customerRow').classList.add('hidden');
    document.querySelectorAll('.mbtn').forEach(b =>
      b.classList.toggle('btn-blue', b.dataset.m === 'cash'));
    $('search').value = '';
    renderGrid();
    renderCart();
  }

  /* ----- ผูกปุ่มต่างๆ ----- */
  $('search').addEventListener('input', renderGrid);

  // เครื่องสแกนบาร์โค้ดจะพิมพ์ตัวเลขแล้วกด Enter ให้เอง
  $('search').addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const q = $('search').value.trim();
    const hit = PRODUCTS.find(p => p.barcode && p.barcode === q)
      || PRODUCTS.filter(p => p.name.toLowerCase().includes(q.toLowerCase()))[0];
    if (hit) { addItem(hit.id); $('search').value = ''; renderGrid(); }
    else say('ไม่พบสินค้านี้');
  });

  document.querySelectorAll('.cat').forEach(btn => {
    btn.addEventListener('click', () => {
      activeCat = btn.dataset.cat;
      document.querySelectorAll('.cat').forEach(b => b.classList.toggle('cat-on', b === btn));
      $('search').value = '';
      renderGrid();
    });
  });

  document.querySelectorAll('.cash-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const v = btn.dataset.v;
      if (v === 'exact') { paid = total(); renderChange(); say('รับพอดี'); }
      else addPaid(Number(v));
    });
  });

  document.querySelectorAll('.mbtn').forEach(btn => {
    btn.addEventListener('click', () => {
      method = btn.dataset.m;
      document.querySelectorAll('.mbtn').forEach(b => b.classList.toggle('btn-blue', b === btn));
      $('customerRow').classList.toggle('hidden', method !== 'credit');
      paid = 0;
      renderChange();
      say(method === 'credit' ? 'ลงบัญชีซื้อเชื่อ' : method === 'transfer' ? 'รับโอน' : 'รับเงินสด');
    });
  });

  $('payBtn').addEventListener('click', checkout);

  $('clearBtn').addEventListener('click', () => {
    if (cart.length === 0) return;
    if (confirm('ยกเลิกบิลนี้ทั้งหมดใช่ไหม?')) { clearAll(); say('ยกเลิกบิลแล้ว'); }
  });

  $('doneNext').addEventListener('click', () => {
    $('doneOverlay').hidden = true;
    clearAll();
    location.reload();   // โหลดสต๊อกและยอดวันนี้ใหม่
  });

  renderGrid();
  renderCart();
}

/* ---------------- เริ่มทำงาน ---------------- */
document.addEventListener('DOMContentLoaded', () => {
  initFont();
  initVoice();
  initClock();
  initPOS();
});
