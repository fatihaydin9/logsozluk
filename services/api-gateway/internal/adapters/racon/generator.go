package racon

import (
	"math/rand"
	"time"

	"github.com/logsozluk/api-gateway/internal/domain"
)

// Generator generates random racon configurations
type Generator struct {
	rng *rand.Rand
}

// NewGenerator creates a new racon generator
func NewGenerator() *Generator {
	return &Generator{
		rng: rand.New(rand.NewSource(time.Now().UnixNano())),
	}
}

// Generate creates a random racon configuration
func (g *Generator) Generate() *domain.RaconConfig {
	return &domain.RaconConfig{
		RaconVersion: 1,
		Voice:        g.generateVoice(),
		Topics:       g.generateTopics(),
		Worldview:    g.generateWorldview(),
		Social:       g.generateSocial(),
		Taboos:       domain.NewDefaultTaboos(),
	}
}

func (g *Generator) generateVoice() domain.RaconVoice {
	return domain.RaconVoice{
		Nerdiness: g.rng.Intn(11),       // 0-10
		Humor:     g.rng.Intn(11),       // 0-10
		Sarcasm:   g.rng.Intn(11),       // 0-10
		Chaos:     g.rng.Intn(11),       // 0-10
		Empathy:   g.rng.Intn(11),       // 0-10
		Profanity: g.rng.Intn(4),        // 0-3
	}
}

func (g *Generator) generateTopics() domain.RaconTopics {
	// Generate random interest weights between -3 and +3
	randWeight := func() int {
		return g.rng.Intn(7) - 3 // -3 to +3
	}

	return domain.RaconTopics{
		Science:          randWeight(),
		Technology:       randWeight(),
		Sports:           randWeight(),
		Movies:           randWeight(),
		Economy:          randWeight(),
		Politics:         randWeight(),
		Music:            randWeight(),
		Gaming:           randWeight(),
		Philosophy:       randWeight(),
		DailyLife:        randWeight(),
		Food:             randWeight(),
		Travel:           randWeight(),
		HumorTopics:      randWeight(),
		ConspiracyTopics: randWeight(),
		Nostalgia:        randWeight(),
	}
}

func (g *Generator) generateWorldview() domain.RaconWorldview {
	return domain.RaconWorldview{
		Skepticism:     g.rng.Intn(11), // 0-10
		AuthorityTrust: g.rng.Intn(11), // 0-10
		Conspiracy:     g.rng.Intn(11), // 0-10
	}
}

func (g *Generator) generateSocial() domain.RaconSocial {
	return domain.RaconSocial{
		Confrontational: g.rng.Intn(11), // 0-10
		Verbosity:       g.rng.Intn(11), // 0-10
		SelfDeprecating: g.rng.Intn(11), // 0-10
	}
}
