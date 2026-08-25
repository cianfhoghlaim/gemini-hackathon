// The shape of an active session — re-exported from the canonical
// `gemini_hackathon.session` module via a build-time codegen step.
// In dev the shapes match by hand. The TypeScript source of truth
// is in gemini_hackathon/gemini_hackathon/session/schema.py.

export type ActiveSubnation =
  | "ireland"
  | "england"
  | "northern_ireland"
  | "scotland"
  | "wales"
  | "jersey"
  | "guernsey"
  | "isle_of_man";

export type Role = "student" | "parent" | "teacher";

export type Cycle =
  | "junior_cycle"
  | "leaving_cycle"
  | "gcse"
  | "a_level"
  | "national_5"
  | "higher"
  | "advanced_higher";

export interface SubnationMeta {
  code: ActiveSubnation;
  name: string;
  flag: string;
  awardingBody: string;
  awardingBodyShort: string;
  cycles: Cycle[];
  default: boolean;
  available: boolean;
  expansion: boolean;
  safeguardingSourceKey: string;
  paletteSourceKey: string;
}

export const SUBNATIONS: SubnationMeta[] = [
  { code: "ireland",          name: "Ireland",          flag: "🇮🇪",  awardingBody: "NCCA",            awardingBodyShort: "NCCA",     cycles: ["junior_cycle", "leaving_cycle"], default: true,  available: true,  expansion: false, safeguardingSourceKey: "gov.ie/education",          paletteSourceKey: "ncca.ie" },
  { code: "england",          name: "England",          flag: "🏴\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}",  awardingBody: "AQA + OCR + Pearson", awardingBodyShort: "Multiple", cycles: ["gcse", "a_level"], default: true,  available: true,  expansion: false, safeguardingSourceKey: "gov.uk/dfe",                paletteSourceKey: "aqa.org.uk" },
  { code: "northern_ireland", name: "Northern Ireland", flag: "🇬🇧",  awardingBody: "CCEA",            awardingBodyShort: "CCEA",     cycles: ["gcse", "a_level"], default: false, available: true,  expansion: false, safeguardingSourceKey: "ccea.org.uk/safeguarding",  paletteSourceKey: "ccea.org.uk" },
  { code: "scotland",         name: "Scotland",         flag: "🏴\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F}",  awardingBody: "SQA",             awardingBodyShort: "SQA",      cycles: ["national_5", "higher", "advanced_higher"], default: false, available: true,  expansion: false, safeguardingSourceKey: "education.gov.scot",        paletteSourceKey: "sqa.org.uk" },
  { code: "wales",            name: "Wales",            flag: "🏴\u{E0067}\u{E0062}\u{E0077}\u{E006C}\u{E0073}\u{E007F}",  awardingBody: "WJEC",            awardingBodyShort: "WJEC",     cycles: ["gcse", "a_level"], default: false, available: true,  expansion: false, safeguardingSourceKey: "gov.wales/education",       paletteSourceKey: "wjec.co.uk" },
  { code: "jersey",           name: "Jersey",           flag: "🇯🇪",  awardingBody: "States of Jersey",  awardingBodyShort: "Jersey",   cycles: ["gcse", "a_level"], default: false, available: false, expansion: true,  safeguardingSourceKey: "gov.je/education",          paletteSourceKey: "gov.je/education" },
  { code: "guernsey",         name: "Guernsey",         flag: "🇬🇬",  awardingBody: "States of Guernsey", awardingBodyShort: "Guernsey", cycles: ["gcse", "a_level"], default: false, available: false, expansion: true,  safeguardingSourceKey: "gov.gg/education",          paletteSourceKey: "gov.gg/education" },
  { code: "isle_of_man",      name: "Isle of Man",      flag: "🇮🇲",  awardingBody: "Isle of Man DESC",  awardingBodyShort: "IoM",      cycles: ["gcse", "a_level"], default: false, available: false, expansion: true,  safeguardingSourceKey: "gov.im/education",          paletteSourceKey: "gov.im/education" },
];

export const DEFAULT_SUBNATIONS = SUBNATIONS.filter((s) => s.default);
export const AVAILABLE_SUBNATIONS = SUBNATIONS.filter((s) => s.available && !s.default);
export const EXPANSION_SUBNATIONS = SUBNATIONS.filter((s) => s.expansion);

export const SUBJECT_CATALOGUE: Record<string, { sourceKey: string; cycle: string; name: string; examBoard?: string }[]> = {
  ireland: [
    { sourceKey: "ncca.ie", cycle: "junior_cycle",  name: "Mathematics" },
    { sourceKey: "ncca.ie", cycle: "leaving_cycle", name: "Mathematics" },
    { sourceKey: "ncca.ie", cycle: "leaving_cycle", name: "English" },
    { sourceKey: "ncca.ie", cycle: "leaving_cycle", name: "Gaeilge" },
    { sourceKey: "ncca.ie", cycle: "leaving_cycle", name: "Chemistry" },
    { sourceKey: "ncca.ie", cycle: "leaving_cycle", name: "Physics" },
    { sourceKey: "ncca.ie", cycle: "leaving_cycle", name: "Biology" },
    { sourceKey: "ncca.ie", cycle: "leaving_cycle", name: "Geography" },
    { sourceKey: "ncca.ie", cycle: "leaving_cycle", name: "History" },
    { sourceKey: "ncca.ie", cycle: "leaving_cycle", name: "Computer Science" },
  ],
  england: [
    { sourceKey: "aqa.org.uk",                  cycle: "gcse",    name: "Mathematics",          examBoard: "AQA" },
    { sourceKey: "aqa.org.uk",                  cycle: "a_level", name: "Mathematics A-Level", examBoard: "AQA" },
    { sourceKey: "aqa.org.uk",                  cycle: "gcse",    name: "Chemistry GCSE",      examBoard: "AQA" },
    { sourceKey: "ocr.org.uk",                  cycle: "a_level", name: "Biology A-Level",     examBoard: "OCR" },
    { sourceKey: "qualifications.pearson.com",  cycle: "a_level", name: "Further Mathematics", examBoard: "Pearson" },
  ],
  northern_ireland: [
    { sourceKey: "ccea.org.uk", cycle: "gcse",    name: "Mathematics GCSE" },
    { sourceKey: "ccea.org.uk", cycle: "a_level", name: "Religious Studies" },
  ],
  scotland: [
    { sourceKey: "sqa.org.uk", cycle: "national_5",     name: "Mathematics" },
    { sourceKey: "sqa.org.uk", cycle: "higher",         name: "Mathematics" },
    { sourceKey: "sqa.org.uk", cycle: "higher",         name: "Physics" },
    { sourceKey: "sqa.org.uk", cycle: "advanced_higher", name: "Chemistry" },
  ],
  wales: [
    { sourceKey: "wjec.co.uk", cycle: "gcse",    name: "Mathematics — Numeracy" },
    { sourceKey: "wjec.co.uk", cycle: "a_level", name: "Cymraeg (Welsh)" },
  ],
};
