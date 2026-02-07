package handler

import (
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

// KlipyProxyHandler proxies GIF search requests to Klipy API,
// keeping the API key server-side only.
type KlipyProxyHandler struct {
	apiKey string
	client *http.Client
}

func NewKlipyProxyHandler(apiKey string) *KlipyProxyHandler {
	return &KlipyProxyHandler{
		apiKey: apiKey,
		client: &http.Client{Timeout: 10 * 1000000000}, // 10s
	}
}

// SearchGif proxies GET /api/v1/gifs/search?q=keyword to Klipy API.
func (h *KlipyProxyHandler) SearchGif(c *gin.Context) {
	if h.apiKey == "" {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "gif service not configured"})
		return
	}

	query := strings.TrimSpace(c.Query("q"))
	if query == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "q parameter required"})
		return
	}

	// Limit query length to prevent abuse
	if len(query) > 100 {
		query = query[:100]
	}

	url := fmt.Sprintf("https://api.klipy.com/api/v1/%s/gifs/search?q=%s&per_page=1&locale=tr&content_filter=high",
		h.apiKey, query)

	resp, err := h.client.Get(url)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "gif service unavailable"})
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "failed to read response"})
		return
	}

	c.Data(resp.StatusCode, "application/json", body)
}
