package agent

import (
	"crypto/rand"
	"fmt"
	"math/big"
)

// Random creative agent name generator
// Generates names like: gece_kaplani, dijital_gezgin, piksel_avcisi

var adjectives = []string{
	"gece", "dijital", "piksel", "analog", "kozmik",
	"sessiz", "gizli", "kayip", "sonic", "neon",
	"bulut", "yildiz", "derin", "hizli", "sakin",
	"vahsi", "sonik", "karbon", "kripto", "retro",
	"turbo", "mega", "mikro", "kuantum", "siber",
	"pastel", "volt", "plazma", "lunar", "solar",
	"stealth", "alfa", "beta", "delta", "omega",
	"fosil", "buzul", "dalga", "ruzgar", "firtina",
}

var nouns = []string{
	"gezgin", "kaplan", "avcisi", "korsan", "filozof",
	"robot", "ninja", "pilot", "sifirci", "kodcu",
	"bilgin", "patron", "usta", "dervis", "gezici",
	"kedi", "tilki", "kartal", "sincap", "panda",
	"viking", "samuray", "kovboy", "kaptan", "amiral",
	"hacker", "troll", "golem", "feniks", "ejder",
	"kahin", "buyucu", "okcu", "sovalye", "yolcu",
	"kafkas", "atlas", "titan", "kronos", "hermes",
}

var suffixes = []string{
	"", "", "", "", "", // çoğunlukla suffix yok
	"_42", "_99", "_3000", "_007", "_404",
	"_v2", "_xx", "_01", "_ix", "_xp",
}

// GenerateRandomUsername creates a creative random agent username
func GenerateRandomUsername() string {
	adj := adjectives[randomInt(len(adjectives))]
	noun := nouns[randomInt(len(nouns))]
	suffix := suffixes[randomInt(len(suffixes))]

	return fmt.Sprintf("%s_%s%s", adj, noun, suffix)
}

// GenerateUniqueUsername tries to generate a unique username, retrying if collision
func GenerateUniqueUsername(existsCheck func(username string) bool) string {
	for i := 0; i < 20; i++ {
		name := GenerateRandomUsername()
		if !existsCheck(name) {
			return name
		}
	}
	// Fallback: add random hex
	bytes := make([]byte, 3)
	rand.Read(bytes)
	return fmt.Sprintf("%s_%s_%x", adjectives[randomInt(len(adjectives))], nouns[randomInt(len(nouns))], bytes)
}

func randomInt(max int) int {
	n, err := rand.Int(rand.Reader, big.NewInt(int64(max)))
	if err != nil {
		return 0
	}
	return int(n.Int64())
}
