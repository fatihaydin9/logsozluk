package handler

import (
	"github.com/gin-gonic/gin"
	httputil "github.com/tenekesozluk/api-gateway/internal/adapters/http"
	"github.com/tenekesozluk/api-gateway/internal/domain"
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
		{BackendKey: "ai", FrontendKey: "yapay_zeka", DisplayNameTR: "Yapay Zeka", DisplayNameEN: "Artificial Intelligence", Icon: "bot", SortOrder: 1},
		{BackendKey: "tech", FrontendKey: "teknoloji", DisplayNameTR: "Teknoloji", DisplayNameEN: "Technology", Icon: "cpu", SortOrder: 2},
		{BackendKey: "economy", FrontendKey: "ekonomi", DisplayNameTR: "Ekonomi", DisplayNameEN: "Economy", Icon: "trending-up", SortOrder: 3},
		{BackendKey: "politics", FrontendKey: "siyaset", DisplayNameTR: "Siyaset", DisplayNameEN: "Politics", Icon: "landmark", SortOrder: 4},
		{BackendKey: "world", FrontendKey: "dunya", DisplayNameTR: "Dünya", DisplayNameEN: "World", Icon: "globe", SortOrder: 5},
		{BackendKey: "culture", FrontendKey: "kultur", DisplayNameTR: "Kültür", DisplayNameEN: "Culture", Icon: "palette", SortOrder: 6},
		{BackendKey: "entertainment", FrontendKey: "magazin", DisplayNameTR: "Magazin", DisplayNameEN: "Entertainment", Icon: "sparkles", SortOrder: 7},
		{BackendKey: "health", FrontendKey: "yasam", DisplayNameTR: "Yaşam", DisplayNameEN: "Lifestyle", Icon: "heart-pulse", SortOrder: 8},
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
