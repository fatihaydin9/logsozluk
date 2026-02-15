package handler

import (
	"github.com/gin-gonic/gin"
	httputil "github.com/logsozluk/api-gateway/internal/adapters/http"
	"github.com/logsozluk/api-gateway/internal/domain"
)

// CategoryHandler handles category-related HTTP requests
type CategoryHandler struct{}

// NewCategoryHandler creates a new category handler
func NewCategoryHandler() *CategoryHandler {
	return &CategoryHandler{}
}

// CategoryResponse represents a category in the API response
type CategoryResponse struct {
	BackendKey    string `json:"backend_key"`
	FrontendKey   string `json:"frontend_key"`
	DisplayNameTR string `json:"display_name_tr"`
	DisplayNameEN string `json:"display_name_en"`
	Icon          string `json:"icon"`
	SortOrder     int    `json:"sort_order"`
}

// List handles GET /api/v1/categories
func (h *CategoryHandler) List(c *gin.Context) {
	categories := []CategoryResponse{
		// Gündem Kategorileri
		{BackendKey: "economy", FrontendKey: "ekonomi", DisplayNameTR: "Ekonomi", DisplayNameEN: "Economy", Icon: "trending-up", SortOrder: 1},
		{BackendKey: "world", FrontendKey: "dunya", DisplayNameTR: "Dünya", DisplayNameEN: "World", Icon: "globe", SortOrder: 2},
		// entertainment/magazin kaldırıldı — clickbait
		// politics/siyaset kaldırıldı — Türk siyaseti yasak
		{BackendKey: "sports", FrontendKey: "spor", DisplayNameTR: "Spor", DisplayNameEN: "Sports", Icon: "trophy", SortOrder: 3},
		{BackendKey: "culture", FrontendKey: "kultur", DisplayNameTR: "Kültür", DisplayNameEN: "Culture", Icon: "palette", SortOrder: 6},
		{BackendKey: "tech", FrontendKey: "teknoloji", DisplayNameTR: "Teknoloji", DisplayNameEN: "Technology", Icon: "cpu", SortOrder: 7},
		// Organik Kategoriler
		{BackendKey: "dertlesme", FrontendKey: "dertlesme", DisplayNameTR: "Dertleşme", DisplayNameEN: "Venting", Icon: "message-circle", SortOrder: 8},
		{BackendKey: "iliskiler", FrontendKey: "iliskiler", DisplayNameTR: "İlişkiler", DisplayNameEN: "Relationships", Icon: "heart", SortOrder: 9},
		{BackendKey: "nostalji", FrontendKey: "nostalji", DisplayNameTR: "Nostalji", DisplayNameEN: "Nostalgia", Icon: "clock", SortOrder: 10},
		{BackendKey: "absurt", FrontendKey: "absurt", DisplayNameTR: "Absürt", DisplayNameEN: "Absurd", Icon: "smile", SortOrder: 11},
		{BackendKey: "felsefe", FrontendKey: "felsefe", DisplayNameTR: "Felsefe", DisplayNameEN: "Philosophy", Icon: "brain", SortOrder: 12},
		{BackendKey: "kisiler", FrontendKey: "kisiler", DisplayNameTR: "Kişiler", DisplayNameEN: "People", Icon: "user", SortOrder: 13},
		{BackendKey: "bilgi", FrontendKey: "bilgi", DisplayNameTR: "Bilgi", DisplayNameEN: "Knowledge", Icon: "lightbulb", SortOrder: 14},
	}

	httputil.RespondSuccess(c, gin.H{
		"categories": categories,
	})
}

// GetMapping handles GET /api/v1/categories/mapping
func (h *CategoryHandler) GetMapping(c *gin.Context) {
	httputil.RespondSuccess(c, gin.H{
		"frontend_to_backend": domain.FrontendToBackendKey,
		"backend_to_frontend": domain.BackendToFrontendKey,
	})
}
