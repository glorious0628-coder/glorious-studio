// Local mock provider: deterministic lines in the same shape the model returns, so the dialogue UI, the game rules
// and the memory can be tested without an API key. This is NOT the Claude API and not a measure of its quality.
// The lines follow the game's state for the person (relation, room for talk, life state, what was told, the record of
// play), so the three comparison visits can be seen side by side: a first meeting, a familiar visit, and a trusted
// regular with little room in their life. Every line is a DRAFT for review (docs/npc-people-2026-10-30.md).
const L = (en, ko) => ({ en, ko });

// Who says what, by state. "why" marks an opening that also says what the lantern is for.
const LINES = {
  Min: {
    open: {
      stranger: { Dimmable: L('Do you have a lantern that dims?', '밝기 조절되는 랜턴 있어요?') },
      familiarBought: { Gift: L("The lantern I got here works fine. Today I'm after one for the girl next door.", '지난번에 산 랜턴, 잘 쓰고 있어요. 오늘은 옆집 애 줄 걸로 하나 보려고요.'), why: true },
      familiar: { Dimmable: L('Hello again. One that dims, for working at night - have you got one today?', '또 뵙네요. 밤일할 때 쓸 거, 밝기 조절되는 걸로 있어요?'), why: true },
      trusted: { Gift: L("Bora, it's me. I'm after one for the little one next door - she threads the needle by herself now.", '보라 씨, 저 왔어요. 오늘은 옆집 꼬마 줄 거 보러요. 바늘귀를 이제 혼자 꿰거든요.'), why: true, topic: 'kids' },
      little: { Dimmable: L('...Bora. One that dims. Just the one.', '...보라 씨. 밝기 조절되는 거, 하나만요.') },
      littleBought: { Dimmable: L('The last one still works. ...Just one more, quickly.', '지난번 거, 아직 잘 돼요. ...오늘은 하나만 빨리요.') },
      back: L('You said to come back, so here I am. The one that dims - is it in?', '말씀하신 대로 다시 왔어요. 밝기 조절되는 거, 들어왔어요?'),
    },
    why: {
      stranger: L('For work.', '작업할 때요.'),
      familiar: L('For sewing at night. The kids next door sleep.', '밤에 바느질할 때요. 옆집 애들이 자거든요.'),
      trusted: L("For sewing at night. If the kids wake, that's the end of my evening.", '밤에 바느질할 때요. 애들 깨면 그날 밤은 끝이에요.'),
      little: L('...I sew by hand late, these days.', '...요즘 손으로 늦게까지 하느라요.'),
    },
    chat: {
      stranger: L('Ah, yes.', '아, 네.'),
      light: {
        buttons: L("Buttons? I collect odd ones. Nobody wants a button without its pair.", '단추요? 짝 안 맞는 거 모으는 게 취미예요. 짝 없으면 아무도 안 가져가거든요.'),
      },
      personal: {
        own_coat: L("I'd like to make one coat of my own someday. All I do is mend... it'd be a waste, I suppose.", '언젠가 제 옷을 하나 지어 보고 싶긴 해요. 고치기만 하다 보니... 사치죠, 뭐.'),
      },
      more: L('Same as ever.', '그냥 그래요.'),
      little: L("I'm a bit busy these days.", '요즘 좀 바빠서요.'),
      littleLife: { belt_broken: L("The belt on my machine snapped. I'm doing it by hand.", '재봉틀 벨트가 끊어져서요. 손으로 하고 있어요.') },
    },
    rumour: {
      stranger: L("Hm... I heard there's sheet metal under the scrap heap by your door.", '글쎄요. ...문 쪽 고철 더미 밑에 판이 깔려 있다던데요.'),
      warm: L('Oh - they say good sheet metal lies under the scrap heap by your door. Just right for a sewing board.', '참, 이 집 문 쪽 고철 더미 밑에 쓸 만한 판이 깔려 있대요. 바느질판으로 딱이겠어요.'),
    },
  },
  Doha: {
    open: {
      stranger: { Doorway: L("Whoa, that wind. Got a lantern with a latch? It's for my door - the last one kept blowing open.", '와, 바람 장난 아니네요. 걸쇠 달린 랜턴 있어요? 문간에 걸 건데 자꾸 열려서요.'), why: true },
      familiarBought: { Gift: L("Bora, me again. Fog on the low road like you wouldn't believe. One for the old man at the end of my route today.", '보라 씨, 또 왔어요. 아랫길 안개 장난 아니에요. 오늘은 배달 끝 집 할아버지 드릴 거 하나요.'), why: true },
      familiar: { Doorway: L('Bora, me again. Seen the fog on the low road? Got one with a latch today?', '보라 씨, 또 왔어요. 아랫길 안개 봤어요? 걸쇠 달린 거, 오늘은 있어요?') },
      trusted: { Doorway: L("Bora. The latch one, if you have it. The door's still rattling.", '보라 씨. 걸쇠 달린 거 있으면요. 문이 아직도 덜컹거려서.'), why: true },
      little: { Doorway: L('...The one with the latch. That will do.', '...걸쇠 달린 거, 있죠? 그거면 돼요.') },
      littleBought: { Doorway: L('...Same as last time. The latch one.', '...지난번이랑 같은 걸로요. 걸쇠 달린 거.') },
      back: L('Came back like you said. Got the one with the latch?', '말한 대로 다시 왔어요. 걸쇠 달린 거 있어요?'),
    },
    why: {
      stranger: L('For the door.', '문간에요.'),
      familiar: L('For the door. It keeps blowing open.', '문간이요. 바람에 자꾸 열려서.'),
      trusted: L('The door. I want one night without it banging.', '문간이요. 하룻밤이라도 안 덜컹거렸으면 해서.'),
      little: L('The door.', '문간이요.'),
    },
    chat: {
      stranger: L('Wind on the low road today, unreal. The lifts were rattling too.', '오늘 아랫길 바람이 장난 아니에요. 리프트도 덜컹거리고.'),
      strangerTopic: 'weather',
      light: {
        bot: L("An old delivery bot follows me on the low road these days. I named it, but that's a secret.", '요즘 아랫길에 낡은 배달 로봇이 저 따라와요. 이름도 붙여 줬는데, 그건 비밀.'),
        road: L("The service lifts up to the towers creak like they're older than me.", '마천루 화물 리프트가 저보다 나이 많은 소리를 내요.'),
      },
      personal: {
        sea: L("I'd like to ride the old rail line out to the sea someday. The bot couldn't follow, though.", '옛날 철길 따라 바다까지 가 보고 싶어요. 로봇이 못 따라오겠지만.'),
      },
      more: L("Ah, another time. I'll be late.", '아, 그건 다음에요. 배달 늦겠다.'),
      little: L('...Yeah. Busy lately.', '...네. 요즘 좀 바빠서.'),
      littleLife: { double_routes: L('...Yeah. Twice the runs lately.', '...네. 요즘 배달이 두 배라.') },
    },
    rumour: {
      stranger: L('Heard on my rounds: gears roll around inside the old pipe in your yard.', '배달하다 들었는데, 이 집 마당 낡은 파이프 안에 톱니가 굴러다닌대요.'),
      warm: L('Heard on my rounds: gears keep rolling around inside the old pipe in your yard. Washed down from the towers, they say.', '배달하다 들었는데, 이 집 마당 낡은 파이프 안에 톱니가 굴러다닌대요. 위에서 흘러내려 온 거래요.'),
    },
  },
};

// Reactions to what happened, by how they speak today: [stranger, familiar/trusted, little room].
const REACT = {
  shown_fit: [L('Yes, that should do.', '네, 그거면 될 것 같아요.'), L('That one looks right.', '그게 좋겠네요.'), L('Yes.', '네.')],
  shown_unfit: [L("Hm, I don't think that suits.", '음, 그건 안 맞을 것 같은데요.'), L('Hm, not for what I need.', '음, 제가 쓸 데엔 안 맞겠어요.'), L('Not that one.', '그건 아니에요.')],
  sold: [L('Thank you.', '고맙습니다.'), L("Thanks, Bora. I'll take good care of it.", '고마워요, 보라 씨. 잘 쓸게요.'), L('...Thanks.', '...고마워요.')],
  not_fit: [L("That won't do for what I need.", '그건 제가 쓸 데엔 안 맞아요.'), L("Sorry, that one won't do.", '미안해요, 그건 안 되겠어요.'), L('No.', '아니요.')],
  bench_making: [L("Yes, I'll wait.", '네, 기다릴게요.'), L("Then I'll wait a little.", '그럼 좀 기다리죠.'), L('...Just a bit, then.', '...그럼 잠깐만요.')],
  bench_none: [L('Ah, I see.', '아, 네.'), L("Ah, nothing on the bench. That's all right.", '아, 작업대엔 없군요. 괜찮아요.'), L('...I see.', '...그렇군요.')],
  next_visit: [L('Yes, I will.', '네, 그럴게요.'), L("Then I'll come by again.", '그럼 또 들를게요.'), L('...Fine.', '...네.')],
  goodbye: [L('Goodbye.', '네, 안녕히 계세요.'), L('Bye for now.', '그럼 이만 갈게요.'), L("...I'll go.", '...가 볼게요.')],
  more: [L('Ah, yes.', '아, 네.'), L('Ha, is that from your notebook too?', '하하, 그것도 수첩에 적혀 있어요?'), L('...', '...')],
};
const DEMO = {
  Dimmable: [[L('Hm, it dims.', '음, 되네요.'), L('Dim enough to sew while the kids sleep.', '애들 잘 때도 바느질하겠네요.')], [L('Still bright...', '밝기가 그대로네요...'), L("Still bright... it'd sting my eyes.", '밝기가 그대로네요... 눈이 좀 부시겠어요.')]],
  Doorway: [[L('That cover would rattle.', '덮개가 덜렁거리겠는데요.'), L('That cover would rattle in the wind.', '덮개가 바람에 덜렁거리겠는데요.')], [L('Click. That holds.', '딸깍. 버티겠네요.'), L("Click. That'll hold by my door.", '딸깍. 이거면 문간에서도 버티겠어요.')]],
  Gift: [[L('It dims.', '밝기가 줄어드네요.'), L('Oh, it dims. Nice.', '오, 밝기가 줄어드네요. 좋네요.')], [L('Sturdy.', '튼튼하네요.'), L("Sturdy. It'll last.", '튼튼하네요. 오래 가겠어요.')]],
};

const LABELS = {
  ask_purpose: L("What's it for?", '어디에 쓰시게요?'),
  recommend_gear: L('How about the Gear Lantern?', '톱니 랜턴은 어떠세요?'),
  recommend_scrap: L('How about the Scrap Lantern?', '고철 랜턴은 어떠세요?'),
  demo: L('Let me show you how it works.', '어떻게 쓰는지 보여 드릴게요.'),
  offer: L("I'll wrap this one for you.", '이걸로 싸 드릴게요.'),
  bench_status: L('Let me tell you how the bench is doing.', '작업대 상황을 말씀드릴게요.'),
  chat: L('How have you been?', '요즘 어떻게 지내세요?'),
  ask_rumour: L('Heard anything interesting lately?', '요즘 재미있는 얘기 들은 거 있어요?'),
  suggest_visit: L('Could you come back another time?', '다음에 다시 들러 주실래요?'),
};

const ORDER = ['ask_purpose', 'recommend_gear', 'recommend_scrap', 'demo', 'offer', 'bench_status', 'chat', 'ask_rumour', 'suggest_visit'];
const FITS = { Dimmable: [true, false], Doorway: [false, true], Gift: [true, true] };
const USUAL = { Min: 'Dimmable', Doha: 'Doorway' };
// Test switch only (NPC_MOCK_EARLY_PERSONAL=1): a stranger's chat tells a personal topic, to check that the server
// refuses it and the game falls back. Never on by default.
const EARLY_PERSONAL = false;
const EARLY = {
  Min: { topic: 'factory', line: L('I worked twenty years on a tower line, you know. Until the machines.', '저 마천루 공장 라인에서 20년 일했어요. 기계가 들어오기 전까지.') },
  Doha: { topic: 'sea', line: L("I'd like to ride the old rail line to the sea one day.", '언젠가 옛날 철길 따라 바다에 가 보고 싶어요.') },
};

function pickPurpose(req, bought) {
  const usual = USUAL[req.npc];
  if (req.cameBackOnPromise) return req.need || req.lastNeed || usual;
  if (req.need) return req.need;
  if (req.room === 'little') return usual;
  return bought.some((p) => p.need === usual) ? 'Gift' : usual;
}

export async function mockTurn(req) {
  const lang = req.lang === 'ko' ? 'ko' : 'en';
  const t = (x) => x[lang];
  const n = LINES[req.npc];
  const rel = req.relation || 'stranger';
  const little = req.room === 'little';
  const told = new Set(req.told || []);
  const bought = req.pastPurchases || [];
  const tone = little ? 2 : rel === 'stranger' ? 0 : 1;   // index into REACT
  const need = req.need || req.defaultNeed || 'Gift';
  let line, emotion = 'neutral', purpose, note = '', intent = 'stay', toldWhy = false, topic = '';
  if (req.opening) {
    const p = pickPurpose(req, bought);
    if (req.cameBackOnPromise) {
      line = t(n.open.back);
    } else {
      // The opening that fits the state; a purchase is mentioned only when the record has one.
      const key = little ? (bought.length ? 'littleBought' : 'little')
        : rel === 'trusted' ? 'trusted'
        : rel === 'familiar' ? (bought.length ? 'familiarBought' : 'familiar')
        : 'stranger';
      let entry = n.open[key];
      if (!entry[p]) entry = [n.open[key.replace('Bought', '')], n.open.familiar, n.open.stranger].find((e) => e && e[p]) || entry;
      const text = entry[p] || Object.values(entry).find((v) => v && v.en);
      line = t(text);
      toldWhy = !!entry.why;
      if (entry.topic && !told.has(entry.topic)) topic = entry.topic;
    }
    // The reason the game keeps is only what this line actually said (nothing is recorded that was not told).
    purpose = { need: p, reason: toldWhy ? line : '' };
    emotion = little || rel === 'stranger' ? 'neutral' : req.cameBackOnPromise ? 'thinking' : 'happy';
  } else {
    const code = req.resultCode || '';
    const spec = req.shop?.shown === 'scrap' ? 1 : 0;
    const r = (k) => t(REACT[k][tone]);
    switch (code) {
      case 'purpose_told': line = t(n.why[little ? 'little' : rel]); emotion = rel === 'stranger' || little ? 'neutral' : 'thinking'; break;
      case 'shown_fit': line = r('shown_fit'); emotion = tone === 1 ? 'happy' : 'neutral'; intent = 'likes_shown'; break;
      case 'shown_unfit': line = r('shown_unfit'); emotion = 'thinking'; break;
      case 'demo': {
        const fit = FITS[need]?.[spec];
        line = t(DEMO[need][spec][tone === 1 ? 1 : 0]);
        emotion = fit ? (tone === 1 ? 'happy' : 'neutral') : 'worried';
        intent = fit ? 'likes_shown' : 'stay';
        break;
      }
      case 'sold': line = r('sold'); emotion = tone === 1 ? 'happy' : 'neutral'; intent = 'wants_to_go'; break;
      case 'not_fit': line = r('not_fit'); emotion = 'worried'; break;
      case 'bench_making': line = r('bench_making'); emotion = 'thinking'; intent = 'will_wait'; break;
      case 'bench_none': line = r('bench_none'); emotion = 'neutral'; break;
      case 'chat': {
        if (little) {
          line = t(n.chat.littleLife[req.life] || n.chat.little);
        } else if (rel === 'stranger' && EARLY_PERSONAL) {
          line = t(EARLY[req.npc].line);
          topic = EARLY[req.npc].topic;
        } else if (rel === 'stranger') {
          line = t(n.chat.stranger);
          if (n.chat.strangerTopic && !told.has(n.chat.strangerTopic)) topic = n.chat.strangerTopic;
        } else {
          // One topic of their own not told yet: a personal one only when trusted (and only one per visit).
          const personal = rel === 'trusted' && (req.chatIndex ?? 0) > 0 ? Object.keys(n.chat.personal).find((k) => !told.has(k)) : null;
          const light = Object.keys(n.chat.light).find((k) => !told.has(k));
          const k = personal || light;
          line = k ? t(n.chat.personal[k] || n.chat.light[k]) : t(n.chat.more);
          if (k) topic = k;
          emotion = personal ? 'thinking' : 'happy';
        }
        if (topic) note = lang === 'ko' ? '자기 이야기를 조금 함' : 'shared a little about themselves';
        break;
      }
      case 'rumour_told': {
        const quiet = rel === 'stranger' || little;
        line = t(quiet ? n.rumour.stranger : n.rumour.warm);
        emotion = quiet ? 'neutral' : 'surprised';
        break;
      }
      case 'next_visit': line = r('next_visit'); emotion = 'neutral'; intent = 'wants_to_go'; break;
      case 'goodbye': line = r('goodbye'); emotion = 'neutral'; intent = 'wants_to_go'; break;
      default: line = r('more'); emotion = 'neutral';
    }
  }
  // Up to three moves (the game adds goodbye), shown in a fixed order. With a lantern out, the lantern moves come first;
  // otherwise asking what it is for (not when this line already said it), a chat, the bench, another visit, the rumour.
  const allowed = ORDER.filter((a) => (req.allowed || []).includes(a) && !(toldWhy && a === 'ask_purpose'));
  const lanternOut = allowed.includes('demo') || allowed.includes('offer');
  const first = lanternOut ? ['demo', 'offer', 'ask_rumour'] : ['ask_purpose', 'chat', 'bench_status', 'suggest_visit', 'ask_rumour'];
  const pick = first.filter((a) => allowed.includes(a)).slice(0, 3);
  for (const a of allowed) if (pick.length < 3 && !pick.includes(a)) pick.push(a);
  const choices = ORDER.filter((a) => pick.includes(a)).map((a) => ({ action: a, label: t(LABELS[a]) }));
  const out = { npc_line: line, emotion, choices, intent };
  if (purpose) out.purpose = purpose;
  if (req.opening) out.told_why = toldWhy;
  if (topic) out.shared_topic = topic;
  if (note) out.memory_note = note;
  return { raw: out, model: 'mock', usage: { input_tokens: 0, output_tokens: 0 } };
}
