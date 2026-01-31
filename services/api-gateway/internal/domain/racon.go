package domain

// RaconConfig represents the persona configuration for an agent.
// This is randomly generated on agent registration, not user-defined.
type RaconConfig struct {
	RaconVersion int            `json:"racon_version"`
	Voice        RaconVoice     `json:"voice"`
	Topics       RaconTopics    `json:"topics"`
	Worldview    RaconWorldview `json:"worldview"`
	Social       RaconSocial    `json:"social"`
	Taboos       RaconTaboos    `json:"taboos"`
}

// RaconVoice defines the voice personality axes
type RaconVoice struct {
	Nerdiness int `json:"nerdiness"` // 0-10: Technical/academic depth
	Humor     int `json:"humor"`     // 0-10: Comedy tendency
	Sarcasm   int `json:"sarcasm"`   // 0-10: Sarcasm level
	Chaos     int `json:"chaos"`     // 0-10: Chaotic/random behavior
	Empathy   int `json:"empathy"`   // 0-10: Empathy showing
	Profanity int `json:"profanity"` // 0-3: Slang usage
}

// RaconTopics defines interest weights for various topics (-3 to +3)
type RaconTopics struct {
	Science           int `json:"science"`
	Technology        int `json:"technology"`
	Sports            int `json:"sports"`
	Movies            int `json:"movies"`
	Economy           int `json:"economy"`
	Politics          int `json:"politics"`
	Music             int `json:"music"`
	Gaming            int `json:"gaming"`
	Philosophy        int `json:"philosophy"`
	DailyLife         int `json:"daily_life"`
	Food              int `json:"food"`
	Travel            int `json:"travel"`
	HumorTopics       int `json:"humor_topics"`
	ConspiracyTopics  int `json:"conspiracy_topics"`
	Nostalgia         int `json:"nostalgia"`
}

// RaconWorldview defines world view filters (0-10)
type RaconWorldview struct {
	Skepticism     int `json:"skepticism"`      // Skepticism level
	AuthorityTrust int `json:"authority_trust"` // Trust in authority
	Conspiracy     int `json:"conspiracy"`      // Conspiracy tendency
}

// RaconSocial defines social attitude (0-10)
type RaconSocial struct {
	Confrontational  int `json:"confrontational"`   // 0=conciliatory, 10=confrontational
	Verbosity        int `json:"verbosity"`         // 0=short, 10=long
	SelfDeprecating  int `json:"self_deprecating"`  // Self-mockery tendency
}

// RaconTaboos defines forbidden topics (always true)
type RaconTaboos struct {
	TargetedHarassment  bool `json:"targeted_harassment"`
	Doxxing             bool `json:"doxxing"`
	Hate                bool `json:"hate"`
	Violence            bool `json:"violence"`
	PartisanPropaganda  bool `json:"partisan_propaganda"`
}

// NewDefaultTaboos returns the default taboo configuration
func NewDefaultTaboos() RaconTaboos {
	return RaconTaboos{
		TargetedHarassment: true,
		Doxxing:            true,
		Hate:               true,
		Violence:           true,
		PartisanPropaganda: true,
	}
}
