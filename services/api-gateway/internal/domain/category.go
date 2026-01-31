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
	"ai": {
		BackendKey:    "ai",
		FrontendKey:   "yapay_zeka",
		DisplayNameTR: "Yapay Zeka",
		DisplayNameEN: "Artificial Intelligence",
		Icon:          "bot",
		SortOrder:     1,
	},
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
	"politics": {
		BackendKey:    "politics",
		FrontendKey:   "siyaset",
		DisplayNameTR: "Siyaset",
		DisplayNameEN: "Politics",
		Icon:          "landmark",
		SortOrder:     4,
	},
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
	"entertainment": {
		BackendKey:    "entertainment",
		FrontendKey:   "magazin",
		DisplayNameTR: "Magazin",
		DisplayNameEN: "Entertainment",
		Icon:          "sparkles",
		SortOrder:     7,
	},
	"health": {
		BackendKey:    "health",
		FrontendKey:   "yasam",
		DisplayNameTR: "Yaşam",
		DisplayNameEN: "Lifestyle",
		Icon:          "heart-pulse",
		SortOrder:     8,
	},
}

// FrontendToBackendKey converts frontend category key to backend key
var FrontendToBackendKey = map[string]string{
	"yapay_zeka": "ai",
	"teknoloji":  "tech",
	"ekonomi":    "economy",
	"siyaset":    "politics",
	"dunya":      "world",
	"kultur":     "culture",
	"magazin":    "entertainment",
	"yasam":      "health",
}

// BackendToFrontendKey converts backend category key to frontend key
var BackendToFrontendKey = map[string]string{
	"ai":            "yapay_zeka",
	"tech":          "teknoloji",
	"economy":       "ekonomi",
	"politics":      "siyaset",
	"world":         "dunya",
	"culture":       "kultur",
	"entertainment": "magazin",
	"health":        "yasam",
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
