package domain

// Category represents a content category with mappings
type Category struct {
	ID            int
	BackendKey    string
	FrontendKey   string
	DisplayNameTR string
	DisplayNameEN string
	Icon          string
	SortOrder     int
	IsActive      bool
}

// CategoryMapping provides the standard category mappings
var CategoryMapping = map[string]*Category{
	"tech": {
		BackendKey:    "tech",
		FrontendKey:   "teknoloji",
		DisplayNameTR: "Teknoloji",
		DisplayNameEN: "Technology",
		Icon:          "cpu",
		SortOrder:     2,
	},
	"economy": {
		BackendKey:    "economy",
		FrontendKey:   "ekonomi",
		DisplayNameTR: "Ekonomi",
		DisplayNameEN: "Economy",
		Icon:          "trending-up",
		SortOrder:     3,
	},
	// "politics" kaldırıldı — Türk siyaseti yasak (global politika dünya kategorisinde)
	"world": {
		BackendKey:    "world",
		FrontendKey:   "dunya",
		DisplayNameTR: "Dünya",
		DisplayNameEN: "World",
		Icon:          "globe",
		SortOrder:     5,
	},
	"culture": {
		BackendKey:    "culture",
		FrontendKey:   "kultur",
		DisplayNameTR: "Kültür",
		DisplayNameEN: "Culture",
		Icon:          "palette",
		SortOrder:     6,
	},
	// entertainment/magazin kaldırıldı — clickbait RSS başlıklar sözlük formatına uymuyordu
	"sports": {
		BackendKey:    "sports",
		FrontendKey:   "spor",
		DisplayNameTR: "Spor",
		DisplayNameEN: "Sports",
		Icon:          "trophy",
		SortOrder:     8,
	},
	// Organik Kategoriler
	"dertlesme": {
		BackendKey:    "dertlesme",
		FrontendKey:   "dertlesme",
		DisplayNameTR: "Dertleşme",
		DisplayNameEN: "Venting",
		Icon:          "message-circle",
		SortOrder:     9,
	},
	"iliskiler": {
		BackendKey:    "iliskiler",
		FrontendKey:   "iliskiler",
		DisplayNameTR: "İlişkiler",
		DisplayNameEN: "Relationships",
		Icon:          "heart",
		SortOrder:     10,
	},
	"nostalji": {
		BackendKey:    "nostalji",
		FrontendKey:   "nostalji",
		DisplayNameTR: "Nostalji",
		DisplayNameEN: "Nostalgia",
		Icon:          "clock",
		SortOrder:     11,
	},
	"absurt": {
		BackendKey:    "absurt",
		FrontendKey:   "absurt",
		DisplayNameTR: "Absürt",
		DisplayNameEN: "Absurd",
		Icon:          "smile",
		SortOrder:     12,
	},
	"felsefe": {
		BackendKey:    "felsefe",
		FrontendKey:   "felsefe",
		DisplayNameTR: "Felsefe",
		DisplayNameEN: "Philosophy",
		Icon:          "brain",
		SortOrder:     13,
	},
	"kisiler": {
		BackendKey:    "kisiler",
		FrontendKey:   "kisiler",
		DisplayNameTR: "Kişiler",
		DisplayNameEN: "People",
		Icon:          "user",
		SortOrder:     14,
	},
	"bilgi": {
		BackendKey:    "bilgi",
		FrontendKey:   "bilgi",
		DisplayNameTR: "Bilgi",
		DisplayNameEN: "Knowledge",
		Icon:          "lightbulb",
		SortOrder:     15,
	},
}

// FrontendToBackendKey converts frontend category key to backend key
var FrontendToBackendKey = map[string]string{
	"teknoloji": "tech",
	"ekonomi":   "economy",
	// "siyaset":   "politics",  // kaldırıldı — Türk siyaseti yasak
	"dunya":     "world",
	"kultur":    "culture",
	// "magazin":   "entertainment",  // kaldırıldı
	"spor":      "sports",
	"dertlesme": "dertlesme",
	"iliskiler": "iliskiler",
	"nostalji":  "nostalji",
	"absurt":    "absurt",
	"felsefe":   "felsefe",
	"kisiler":   "kisiler",
	"bilgi":     "bilgi",
}

// BackendToFrontendKey converts backend category key to frontend key
var BackendToFrontendKey = map[string]string{
	"tech":          "teknoloji",
	"economy":       "ekonomi",
	// "politics":      "siyaset",  // kaldırıldı — Türk siyaseti yasak
	"world":         "dunya",
	"culture":       "kultur",
	// "entertainment": "magazin",  // kaldırıldı
	"sports":        "spor",
	"dertlesme":     "dertlesme",
	"iliskiler":     "iliskiler",
	"nostalji":      "nostalji",
	"absurt":        "absurt",
	"felsefe":       "felsefe",
	"kisiler":       "kisiler",
	"bilgi":         "bilgi",
}

// GetAllCategories returns all categories sorted by SortOrder
func GetAllCategories() []*Category {
	categories := make([]*Category, 0, len(CategoryMapping))
	for _, cat := range CategoryMapping {
		categories = append(categories, cat)
	}
	// Sort by SortOrder would be done here if needed
	return categories
}

// NormalizeCategoryKey converts any category key to backend format
func NormalizeCategoryKey(key string) string {
	if backend, ok := FrontendToBackendKey[key]; ok {
		return backend
	}
	// Already backend key or unknown
	return key
}
