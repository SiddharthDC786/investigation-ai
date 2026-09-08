export type Language = 'en' | 'hi'

export const languages: { code: Language; label: string; native: string }[] = [
  { code: 'en', label: 'English', native: 'English' },
  { code: 'hi', label: 'Hindi', native: 'हिन्दी' },
]

export const LANGUAGE_STORAGE_KEY = 'vigil_language'

export type TranslationTree = {
  language: {
    choose: string
    english: string
    hindi: string
  }
  security: {
    confidential: string
    confidentialHi: string
  }
  login: {
    restricted: string
    title: string
    subtitle: string
    badgeId: string
    password: string
    passwordPlaceholder: string
    signIn: string
    error: string
    showDemo: string
    hideDemo: string
    demoInvestigator: string
    demoSupervisor: string
    ruleIdle: string
    ruleAudit: string
    ruleShare: string
  }
  sih: {
    problemId: string
    tagline: string
    loginTagline: string
  }
  connection: {
    live: string
    demo: string
    checking: string
    down: string
    degraded: string
    liveHint: string
    demoHint: string
    downHint: string
  }
  presentation: {
    on: string
    off: string
    hint: string
  }
  stats: {
    people: string
    cases: string
    networks: string
    identityScenarios: string
  }
  demo: {
    title: string
    subtitle: string
    same_name: string
    same_nameDesc: string
    fir_typo: string
    fir_typoDesc: string
    married_name: string
    married_nameDesc: string
    hidden_bridge: string
    hidden_bridgeDesc: string
  }
  topBar: {
    investigator: string
    supervisor: string
    timeLeft: string
    minutesUnit: string
    logout: string
  }
  footer: {
    actionsSaved: string
    endSession: string
  }
  nav: {
    mainMenu: string
    navHint: string
  }
  guide: {
    show: string
    hide: string
    title: string
    subtitle: string
    step: string
  }
  inspector: {
    title: string
    subtitle: string
    emptyTitle: string
    emptyHint: string
    importanceScore: string
    whyFlagged: string
    proofRecords: string
    alsoKnownAsTitle: string
    identityNote: string
    linkedTo: string
    techTitle: string
    techSubtitle: string
    recordId: string
    yourDecision: string
    decisionHint: string
  }
  review: {
    confirm: string
    confirmHint: string
    needsEvidence: string
    needsEvidenceHint: string
    dismiss: string
    dismissHint: string
  }
  entityType: {
    person: string
    phone: string
    account: string
    address: string
  }
  role: {
    suspect: string
    associate: string
    facilitator: string
    witness: string
    complainant: string
    handler: string
  }
  severity: {
    high: string
    medium: string
    low: string
  }
  views: {
    search: ViewCopy
    network: ViewCopy
    timeline: ViewCopy
    risk: ViewCopy
    osint: ViewCopy
    audit: ViewCopy
  }
  network: {
    legendPerson: string
    legendPhone: string
    legendBank: string
    legendRing: string
    bridgeCallout: string
    bridgeTap: string
  }
  timeline: {
    source: string
    empty: string
    apiError: string
  }
  risk: {
    scoreChart: string
    colName: string
    colScore: string
    colPriority: string
    colType: string
    empty: string
    apiError: string
    loading: string
  }
  osint: {
    policy: string
    selectedTarget: string
    selectFirst: string
    availableSearches: string
    runSearch: string
    recentSearches: string
    noSearches: string
    caseLabel: string
  }
  audit: {
    export: string
    exportTitleSupervisor: string
    exportTitleDenied: string
    exportSuccess: string
    exportWatermark: string
    colWhen: string
    colAction: string
    colRecord: string
    colOfficer: string
    empty: string
    chainVerified: string
    chainBroken: string
    chainUnknown: string
  }
  search: {
    nameLabel: string
    namePlaceholder: string
    phoneLabel: string
    phonePlaceholder: string
    areaLabel: string
    areaPlaceholder: string
    roleLabel: string
    roleAll: string
    faceLabel: string
    faceHint: string
    faceScanning: string
    faceMatchResult: string
    faceError: string
    apiError: string
    runSearch: string
    searching: string
    clear: string
    emptyTitle: string
    emptyHint: string
    tryExample: string
    noResults: string
    primaryMatches: string
    relatedPeople: string
    relatedHint: string
    linkedRecords: string
    hopsAway: string
    bridgeLink: string
    bridgeHint: string
    typoHint: string
    multipleTitle: string
    multipleHint: string
    confirmPerson: string
    alsoKnownAs: string
    narrowedToOne: string
    pickPerson: string
  }
}

type ViewCopy = {
  title: string
  hint: string
  header: string
  description: string
}

export const translations: Record<Language, TranslationTree> = {
  en: {
    language: { choose: 'Language', english: 'English', hindi: 'Hindi' },
    security: {
      confidential:
        'Investigation data. Official use only. Do not share outside your case team.',
      confidentialHi: '',
    },
    login: {
      restricted: 'For authorised police & investigation staff only',
      title: 'Vigil',
      subtitle: 'Case investigation system — works on any district PC or tablet',
      badgeId: 'Badge ID',
      password: 'Password',
      passwordPlaceholder: 'Enter password',
      signIn: 'Sign in',
      error: 'Wrong badge ID or password. This attempt is logged.',
      showDemo: 'Show training login (demo only)',
      hideDemo: 'Hide training login (demo only)',
      demoInvestigator: 'Field investigator',
      demoSupervisor: 'Supervisor',
      ruleIdle: 'Auto logout after 30 minutes idle',
      ruleAudit: 'Every action is recorded in the log',
      ruleShare: 'Do not share login or export without permission',
    },
    sih: {
      problemId: 'SIH PS 26189',
      tagline: 'Criminal network analysis for law enforcement',
      loginTagline: 'Smart India Hackathon 2026 — Problem Statement 26189',
    },
    connection: {
      live: 'Live backend',
      demo: 'Demo data',
      checking: 'Checking…',
      down: 'Backend offline',
      degraded: 'Backend degraded',
      liveHint: 'Connected to investigation API',
      demoHint: 'Training mode — mock case data on this device',
      downHint: 'Start backend on port 8000 or check frontend/.env',
    },
    presentation: {
      on: 'Presentation mode',
      off: 'Normal view',
      hint: 'Larger text and buttons for demo / tablet',
    },
    stats: {
      people: '2,000 persons',
      cases: '241 cases',
      networks: '25 complex networks',
      identityScenarios: '40 identity-resolution scenarios',
    },
    demo: {
      title: 'Judge demo — one tap',
      subtitle: 'Run a scripted identity-resolution scenario for the jury',
      same_name: 'Same name collision',
      same_nameDesc: 'Search Rahul — multiple people, pick Mumbai suspect',
      fir_typo: 'FIR spelling error',
      fir_typoDesc: 'Mukkherjee typo resolves to Rahul Mukherjee',
      married_name: 'Married surname change',
      married_nameDesc: 'Meera Iyer ↔ Meera Chopra alias resolution',
      hidden_bridge: 'Hidden bridge (3 persons)',
      hidden_bridgeDesc: 'Confirm Rahul Mumbai → Sunil + Vikram via prepaid SIM only',
    },
    topBar: {
      investigator: 'Investigator',
      supervisor: 'Supervisor',
      timeLeft: 'Time left',
      minutesUnit: 'min',
      logout: 'Logout',
    },
    footer: { actionsSaved: 'All actions saved to log', endSession: 'End session' },
    nav: {
      mainMenu: 'Main menu',
      navHint: 'Tap a menu item. Person details always show on the right side.',
    },
    guide: {
      show: 'Show 6-step guide →',
      hide: 'Hide guide',
      title: 'How to work this case — 6 simple steps',
      subtitle: 'Start with search. Full details stay in the right panel.',
      step: 'Step',
    },
    inspector: {
      title: 'Details panel',
      subtitle: 'Why flagged, proof sources, and your decision',
      emptyTitle: 'Select someone from the map or list',
      emptyHint: 'Tap a person, phone, or bank account. Full evidence appears here.',
      importanceScore: 'importance score (0–100)',
      whyFlagged: 'Why the system flagged this',
      proofRecords: 'Proof from records',
      alsoKnownAsTitle: 'Also recorded as (identity variants)',
      identityNote: 'Officer must confirm before merging profiles — unresolved variants stay separate.',
      linkedTo: 'Linked to',
      techTitle: 'Technical details (optional)',
      techSubtitle: 'Record IDs and system fields — for senior officers or court filing',
      recordId: 'Record ID',
      yourDecision: 'Your decision',
      decisionHint: 'Required before sending case upward. AI suggests — you confirm.',
    },
    review: {
      confirm: 'Yes — flag is correct',
      confirmHint: 'Agree with system suggestion',
      needsEvidence: 'Need more proof',
      needsEvidenceHint: 'Keep watching, gather evidence',
      dismiss: 'Not relevant',
      dismissHint: 'Remove this suggestion',
    },
    entityType: {
      person: 'Person',
      phone: 'Phone',
      account: 'Bank account',
      address: 'Address',
    },
    role: {
      suspect: 'Main suspect',
      associate: 'Known associate',
      facilitator: 'Money / logistics helper',
      witness: 'Witness',
      complainant: 'Complainant',
      handler: 'Handler / controller',
    },
    severity: {
      high: 'High priority',
      medium: 'Medium priority',
      low: 'Lower priority',
    },
    views: {
      search: {
        title: 'Person Search',
        hint: 'Name, phone, area, face',
        header: 'Person Search',
        description:
          'Search by name to find the person and everyone linked to them. Narrow with phone, area, role, or photo.',
      },
      network: {
        title: 'Connection Map',
        hint: 'See links between people & accounts',
        header: 'Connection Map',
        description:
          'Tap any circle or box to see who is linked — person, phone, bank account, or address.',
      },
      timeline: {
        title: 'Event Timeline',
        hint: 'What happened, in date order',
        header: 'Event Timeline',
        description:
          'Calls, payments, and FIR events from oldest to newest. Tap a name to open details.',
      },
      risk: {
        title: 'Priority List',
        hint: 'Who to investigate first',
        header: 'Priority List',
        description:
          'Ranked by connections, money flow, and evidence. Higher score = investigate sooner.',
      },
      osint: {
        title: 'Record Search',
        hint: 'Look up public records (logged)',
        header: 'Record Search',
        description:
          'Run approved lookups on the selected person or account. Every search is saved to the log.',
      },
      audit: {
        title: 'Action Log',
        hint: 'Who did what, and when',
        header: 'Action Log',
        description:
          'Full record of logins, searches, and decisions — for court disclosure and review.',
      },
    },
    network: {
      legendPerson: 'Person',
      legendPhone: 'Phone',
      legendBank: 'Bank',
      legendRing: 'Coloured ring = role',
      bridgeCallout:
        'Hidden bridge: prepaid 8871205599 links Mumbai suspect, Pune facilitator & Delhi handler — zero direct calls between them.',
      bridgeTap: 'Tap the highlighted burner SIM to see fusion explainability.',
    },
    timeline: { source: 'Source', empty: 'No timeline events for this case yet.', apiError: 'Could not load timeline — check backend connection.' },
    risk: {
      scoreChart: 'Score chart',
      colName: 'Name',
      colScore: 'Score',
      colPriority: 'Priority',
      colType: 'Type',
      empty: 'No risk scores yet — ingest case data first.',
      apiError: 'Could not load risk analysis — check backend connection.',
      loading: 'Computing risk scores…',
    },
    osint: {
      policy: 'Only lawful public records. Every search is saved with your name and time.',
      selectedTarget: 'Selected person / record',
      selectFirst: 'First select someone from the map, timeline, or priority list.',
      availableSearches: 'Available searches',
      runSearch: 'Run search (saved to log)',
      recentSearches: 'Recent searches this session',
      noSearches: 'No searches yet. Results appear here instantly.',
      caseLabel: 'Case',
    },
    audit: {
      export: 'Download report (supervisor)',
      exportTitleSupervisor: 'Supervisor only',
      exportTitleDenied: 'Ask your supervisor to export',
      exportSuccess: 'Disclosure bundle downloaded',
      exportWatermark: 'VIGIL CONFIDENTIAL — court disclosure draft',
      colWhen: 'When',
      colAction: 'What happened',
      colRecord: 'Record',
      colOfficer: 'Officer',
      empty: 'No audit entries yet. OSINT lookups and session actions appear here.',
      chainVerified: 'Hash chain verified',
      chainBroken: 'Hash chain broken — investigate tampering',
      chainUnknown: 'Chain status unknown',
    },
    search: {
      nameLabel: 'Name',
      namePlaceholder: 'e.g. Rahul, Gopal, Meera',
      phoneLabel: 'Phone number',
      phonePlaceholder: 'e.g. 6749921640',
      areaLabel: 'Area / city',
      areaPlaceholder: 'e.g. Mumbai, Indore',
      roleLabel: 'Role filter',
      roleAll: 'All roles',
      faceLabel: 'Face photo (optional)',
      faceHint: 'Upload CCTV or suspect photo — demo match in training mode',
      faceScanning: 'Scanning photo…',
      faceMatchResult: 'Possible match found ({confidence}% confidence)',
      faceError: 'Face scan failed — try again',
      apiError: 'Search failed — check backend connection.',
      runSearch: 'Search',
      searching: 'Searching…',
      clear: 'Clear',
      emptyTitle: 'Search for a person to begin',
      emptyHint: 'Enter a name, phone, or area. Related people and linked phones or accounts appear here.',
      tryExample: 'Try: Rahul · then pick Mumbai · or phone 6749921640 · typo: Mukkherjee',
      noResults: 'No matches — try a different spelling or remove filters',
      primaryMatches: 'Direct matches',
      relatedPeople: 'Related people in network',
      relatedHint: 'Connected through calls, accounts, or case links',
      linkedRecords: 'Linked phones, accounts & locations',
      hopsAway: '{n} link(s) away',
      bridgeLink: 'Hidden bridge',
      bridgeHint: 'Non-obvious link — no direct contact between persons in raw records',
      typoHint:
        'Typos & FIR spelling mistakes are matched automatically (e.g. Mukkherjee → Mukherjee). If many people share a name, use area or phone to pick the right one.',
      multipleTitle: 'Multiple people with this name',
      multipleHint:
        'Compare city, phone, and date of birth below — then tap “This is the person”. Or add area/phone on the left and search again.',
      confirmPerson: 'This is the person — show network',
      alsoKnownAs: 'Also recorded as',
      narrowedToOne: 'Filters narrowed to one person — network shown below.',
      pickPerson: 'Choose the correct person',
    },
  },
  hi: {
    language: { choose: 'भाषा', english: 'English', hindi: 'हिन्दी' },
    security: {
      confidential:
        'जांच डेटा। केवल आधिकारिक उपयोग। अपनी जांच टीम के बाहर साझा न करें।',
      confidentialHi: 'गोपनीय — केवल अधिकृत उपयोग',
    },
    login: {
      restricted: 'केवल अधिकृत पुलिस और जांच कर्मचारियों के लिए',
      title: 'Vigil',
      subtitle: 'मामला जांच प्रणाली — किसी भी जिला PC या टैबलेट पर चलती है',
      badgeId: 'बैज आईडी',
      password: 'पासवर्ड',
      passwordPlaceholder: 'पासवर्ड दर्ज करें',
      signIn: 'लॉगिन करें',
      error: 'गलत बैज आईडी या पासवर्ड। यह प्रयास दर्ज किया गया है।',
      showDemo: 'प्रशिक्षण लॉगिन दिखाएँ (केवल डेमो)',
      hideDemo: 'प्रशिक्षण लॉगिन छिपाएँ',
      demoInvestigator: 'फील्ड जांच अधिकारी',
      demoSupervisor: 'पर्यवेक्षक',
      ruleIdle: '30 मिनट निष्क्रिय रहने पर स्वतः लॉगआउट',
      ruleAudit: 'हर कार्रवाई लॉग में दर्ज होती है',
      ruleShare: 'अनुमति के बिना लॉगिन या निर्यात साझा न करें',
    },
    sih: {
      problemId: 'SIH PS 26189',
      tagline: 'कानून प्रवर्तन के लिए आपराधिक नेटवर्क विश्लेषण',
      loginTagline: 'स्मार्ट इंडिया हैकाथॉन 2026 — समस्या कथन 26189',
    },
    connection: {
      live: 'लाइव बैकएंड',
      demo: 'डेमो डेटा',
      checking: 'जाँच हो रही है…',
      down: 'बैकएंड ऑफलाइन',
      degraded: 'बैकएंड कमज़ोर',
      liveHint: 'जांच API से जुड़ा',
      demoHint: 'प्रशिक्षण — इस डिवाइस पर मॉक डेटा',
      downHint: 'पोर्ट 8000 पर बैकएंड चालू करें या frontend/.env जाँचें',
    },
    presentation: {
      on: 'प्रस्तुति मोड',
      off: 'सामान्य दृश्य',
      hint: 'डेमो / टैबलेट के लिए बड़ा टेक्स्ट और बटन',
    },
    stats: {
      people: '2,000 व्यक्ति',
      cases: '241 मामले',
      networks: '25 जटिल नेटवर्क',
      identityScenarios: '40 पहचान-समाधान परिदृश्य',
    },
    demo: {
      title: 'जज डेमो — एक टैप',
      subtitle: 'जूरी के लिए पहचान-समाधान परिदृश्य चलाएँ',
      same_name: 'एक ही नाम — कई लोग',
      same_nameDesc: 'Rahul खोजें — कई मिलान, Mumbai संदिग्ध चुनें',
      fir_typo: 'FIR वर्तनी त्रुटि',
      fir_typoDesc: 'Mukkherjee टाइपो → Rahul Mukherjee',
      married_name: 'विवाह के बाद उपनाम',
      married_nameDesc: 'Meera Iyer ↔ Meera Chopra उपनाम',
      hidden_bridge: 'छिपा पुल (3 व्यक्ति)',
      hidden_bridgeDesc: 'Rahul Mumbai पुष्टि → prepaid SIM से Sunil + Vikram',
    },
    topBar: {
      investigator: 'जांच अधिकारी',
      supervisor: 'पर्यवेक्षक',
      timeLeft: 'शेष समय',
      minutesUnit: 'मि',
      logout: 'लॉगआउट',
    },
    footer: {
      actionsSaved: 'सभी कार्रवाइयाँ लॉग में सहेजी गईं',
      endSession: 'सत्र समाप्त करें',
    },
    nav: {
      mainMenu: 'मुख्य मेनू',
      navHint: 'मेनू चुनें। व्यक्ति का विवरण हमेशा दाईं ओर दिखता है।',
    },
    guide: {
      show: '6-चरण गाइड दिखाएँ →',
      hide: 'गाइड छिपाएँ',
      title: 'इस मामले पर काम कैसे करें — 6 आसान चरण',
      subtitle: 'पहले खोज से शुरू करें। विवरण दाईं पैनल में रहता है।',
      step: 'चरण',
    },
    inspector: {
      title: 'विवरण पैनल',
      subtitle: 'क्यों चिह्नित, साक्ष्य स्रोत, और आपका निर्णय',
      emptyTitle: 'मैप या सूची से किसी को चुनें',
      emptyHint: 'व्यक्ति, फ़ोन या बैंक खाता टैप करें। पूरा साक्ष्य यहाँ दिखेगा।',
      importanceScore: 'महत्व स्कोर (0–100)',
      whyFlagged: 'सिस्टम ने इसे क्यों चिह्नित किया',
      proofRecords: 'रिकॉर्ड से साक्ष्य',
      alsoKnownAsTitle: 'रिकॉर्ड में ये नाम भी (पहचान variants)',
      identityNote: 'प्रोफ़ाइल मर्ज से पहले अधिकारी की पुष्टि — अनसुलझे variants अलग रहते हैं।',
      linkedTo: 'इनसे जुड़ा है',
      techTitle: 'तकनीकी विवरण (वैकल्पिक)',
      techSubtitle: 'रिकॉर्ड ID और सिस्टम फ़ील्ड — वरिष्ठ अधिकारियों या अदालत के लिए',
      recordId: 'रिकॉर्ड ID',
      yourDecision: 'आपका निर्णय',
      decisionHint: 'मामला ऊपर भेजने से पहले आवश्यक। AI सुझाव देता है — आप पुष्टि करें।',
    },
    review: {
      confirm: 'हाँ — चिह्न सही है',
      confirmHint: 'सिस्टम सुझाव से सहमत',
      needsEvidence: 'और साक्ष्य चाहिए',
      needsEvidenceHint: 'नज़र रखें, साक्ष्य इकट्ठा करें',
      dismiss: 'प्रासंगिक नहीं',
      dismissHint: 'यह सुझाव हटाएँ',
    },
    entityType: {
      person: 'व्यक्ति',
      phone: 'फ़ोन',
      account: 'बैंक खाता',
      address: 'पता',
    },
    role: {
      suspect: 'मुख्य संदिग्ध',
      associate: 'ज्ञात सहयोगी',
      facilitator: 'धन / लॉजिस्टिक्स सहायक',
      witness: 'गवाह',
      complainant: 'शिकायतकर्ता',
      handler: 'हैंडलर / नियंत्रक',
    },
    severity: {
      high: 'उच्च प्राथमिकता',
      medium: 'मध्यम प्राथमिकता',
      low: 'कम प्राथमिकता',
    },
    views: {
      search: {
        title: 'व्यक्ति खोज',
        hint: 'नाम, फ़ोन, क्षेत्र, चेहरा',
        header: 'व्यक्ति खोज',
        description:
          'नाम से व्यक्ति और जुड़े लोग खोजें। फ़ोन, क्षेत्र, भूमिका या फोटो से और संकुचित करें।',
      },
      network: {
        title: 'कनेक्शन मैप',
        hint: 'लोगों और खातों के बीच संबंध देखें',
        header: 'कनेक्शन मैप',
        description:
          'किसी भी गोले या बॉक्स पर टैप करें — व्यक्ति, फ़ोन, बैंक खाता या पता किससे जुड़ा है।',
      },
      timeline: {
        title: 'घटना समयरेखा',
        hint: 'तारीख के क्रम में क्या हुआ',
        header: 'घटना समयरेखा',
        description:
          'कॉल, भुगतान और FIR घटनाएँ पुरानी से नई। नाम टैप करके विवरण खोलें।',
      },
      risk: {
        title: 'प्राथमिकता सूची',
        hint: 'पहले किसकी जांच करें',
        header: 'प्राथमिकता सूची',
        description:
          'संबंध, धन प्रवाह और साक्ष्य के आधार पर क्रम। अधिक स्कोर = पहले जांच।',
      },
      osint: {
        title: 'रिकॉर्ड खोज',
        hint: 'सार्वजनिक रिकॉर्ड खोजें (लॉग होगा)',
        header: 'रिकॉर्ड खोज',
        description:
          'चयनित व्यक्ति या खाते पर अनुमोदित खोज चलाएँ। हर खोज लॉग में सहेजी जाती है।',
      },
      audit: {
        title: 'कार्रवाई लॉग',
        hint: 'किसने क्या और कब किया',
        header: 'कार्रवाई लॉग',
        description:
          'लॉगिन, खोज और निर्णयों का पूरा रिकॉर्ड — अदालत और समीक्षा के लिए।',
      },
    },
    network: {
      legendPerson: 'व्यक्ति',
      legendPhone: 'फ़ोन',
      legendBank: 'बैंक',
      legendRing: 'रंगीन घेरा = भूमिका',
      bridgeCallout:
        'छिपा पुल: prepaid 8871205599 — Mumbai संदिग्ध, Pune सहायक और Delhi हैंडलर (आपस में कोई सीधा कॉल नहीं)।',
      bridgeTap: 'फ्यूजन विवरण के लिए हाइलाइट burner SIM पर टैप करें।',
    },
    timeline: {
      source: 'स्रोत',
      empty: 'इस मामले के लिए अभी कोई टाइमलाइन घटना नहीं।',
      apiError: 'टाइमलाइन लोड नहीं हुई — बैकएंड कनेक्शन जाँचें।',
    },
    risk: {
      scoreChart: 'स्कोर चार्ट',
      colName: 'नाम',
      colScore: 'स्कोर',
      colPriority: 'प्राथमिकता',
      colType: 'प्रकार',
      empty: 'अभी कोई जोखिम स्कोर नहीं — पहले केस डेटा इंगेस्ट करें।',
      apiError: 'जोखिम विश्लेषण लोड नहीं हुआ — बैकएंड कनेक्शन जाँचें।',
      loading: 'जोखिम स्कोर की गणना…',
    },
    osint: {
      policy: 'केवल कानूनी सार्वजनिक रिकॉर्ड। हर खोज आपके नाम और समय के साथ सहेजी जाती है।',
      selectedTarget: 'चयनित व्यक्ति / रिकॉर्ड',
      selectFirst: 'पहले मैप, समयरेखा या प्राथमिकता सूची से किसी को चुनें।',
      availableSearches: 'उपलब्ध खोज',
      runSearch: 'खोज चलाएँ (लॉग में सहेजा जाएगा)',
      recentSearches: 'इस सत्र की हाल की खोज',
      noSearches: 'अभी कोई खोज नहीं। परिणाम तुरंत यहाँ दिखेंगे।',
      caseLabel: 'मामला',
    },
    audit: {
      export: 'रिपोर्ट डाउनलोड (पर्यवेक्षक)',
      exportTitleSupervisor: 'केवल पर्यवेक्षक',
      exportTitleDenied: 'निर्यात के लिए पर्यवेक्षक से पूछें',
      exportSuccess: 'प्रकटीकरण बंडल डाउनलोड हुआ',
      exportWatermark: 'VIGIL गोपनीय — अदालत प्रकटीकरण ड्राफ्ट',
      colWhen: 'कब',
      colAction: 'क्या हुआ',
      colRecord: 'रिकॉर्ड',
      colOfficer: 'अधिकारी',
      empty: 'अभी कोई ऑडिट प्रविष्टि नहीं। OSINT और सत्र कार्रवाइयाँ यहाँ दिखेंगी।',
      chainVerified: 'हैश चेन सत्यापित',
      chainBroken: 'हैश चेन टूटी — छेड़छाड़ की जाँच करें',
      chainUnknown: 'चेन स्थिति अज्ञात',
    },
    search: {
      nameLabel: 'नाम',
      namePlaceholder: 'जैसे Rahul, Gopal, Meera',
      phoneLabel: 'फ़ोन नंबर',
      phonePlaceholder: 'जैसे 6749921640',
      areaLabel: 'क्षेत्र / शहर',
      areaPlaceholder: 'जैसे Mumbai, Indore',
      roleLabel: 'भूमिका फ़िल्टर',
      roleAll: 'सभी भूमिकाएँ',
      faceLabel: 'चेहरे की फोटो (वैकल्पिक)',
      faceHint: 'CCTV या संदिग्ध की फोटो अपलोड करें — प्रशिक्षण में डेमो मिलान',
      faceScanning: 'फोटो स्कैन हो रही है…',
      faceMatchResult: 'संभावित मिलान ({confidence}% विश्वास)',
      faceError: 'फेस स्कैन विफल — पुनः प्रयास करें',
      apiError: 'खोज विफल — बैकएंड कनेक्शन जाँचें।',
      runSearch: 'खोजें',
      searching: 'खोज रहे हैं…',
      clear: 'साफ़ करें',
      emptyTitle: 'शुरू करने के लिए व्यक्ति खोजें',
      emptyHint: 'नाम, फ़ोन या क्षेत्र दर्ज करें। संबंधित लोग और लिंक्ड रिकॉर्ड यहाँ दिखेंगे।',
      tryExample: 'आज़माएँ: Rahul · 6749921640 · Mumbai',
      noResults: 'कोई परिणाम नहीं — अलग वर्तनी या फ़िल्टर हटाएँ',
      primaryMatches: 'प्रत्यक्ष मिलान',
      relatedPeople: 'नेटवर्क में संबंधित लोग',
      relatedHint: 'कॉल, खाते या मामले के लिंक से जुड़े',
      linkedRecords: 'लिंक्ड फ़ोन, खाते और स्थान',
      hopsAway: '{n} कड़ी दूर',
      bridgeLink: 'छिपा पुल',
      bridgeHint: 'अस्पष्ट लिंक — कच्चे रिकॉर्ड में व्यक्तियों के बीच सीधा संपर्क नहीं',
      typoHint:
        'टाइपो और FIR की गलत वर्तनी automatic match होती है (जैसे Mukkherjee → Mukherjee)। एक नाम पर कई लोग हों तो क्षेत्र या फ़ोन से सही व्यक्ति चुनें।',
      multipleTitle: 'इस नाम के कई लोग मिले',
      multipleHint:
        'नीचे शहर, फ़ोन और जन्मतिथि से compare करें — फिर “यही व्यक्ति है” दबाएँ। या बाएँ से क्षेत्र/फ़ोन जोड़कर फिर खोजें।',
      confirmPerson: 'यही व्यक्ति है — नेटवर्क दिखाएँ',
      alsoKnownAs: 'रिकॉर्ड में ये नाम भी',
      narrowedToOne: 'फ़िल्टर से एक व्यक्ति बचा — नेटवर्क नीचे है।',
      pickPerson: 'सही व्यक्ति चुनें',
    },
  },
}
