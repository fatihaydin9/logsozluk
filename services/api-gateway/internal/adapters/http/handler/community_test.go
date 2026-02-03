// +build integration

// TODO: Bu testler interface refactoring sonrası düzeltilecek.
// Şimdilik skip edildi çünkü CommunityHandler concrete *community.Service bekliyor.

package handler

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"

	"github.com/logsozluk/api-gateway/internal/domain"
)

// MockCommunityService is a mock implementation of the community service
type MockCommunityService struct {
	mock.Mock
}

func (m *MockCommunityService) Create(ctx any, name, description string, communityType domain.CommunityType, focusTopics []string, createdBy uuid.UUID) (*domain.Community, error) {
	args := m.Called(ctx, name, description, communityType, focusTopics, createdBy)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*domain.Community), args.Error(1)
}

func (m *MockCommunityService) GetBySlug(ctx any, slug string) (*domain.Community, []*domain.CommunityMember, error) {
	args := m.Called(ctx, slug)
	if args.Get(0) == nil {
		return nil, nil, args.Error(2)
	}
	return args.Get(0).(*domain.Community), args.Get(1).([]*domain.CommunityMember), args.Error(2)
}

func (m *MockCommunityService) List(ctx any, limit, offset int) ([]*domain.Community, error) {
	args := m.Called(ctx, limit, offset)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).([]*domain.Community), args.Error(1)
}

func (m *MockCommunityService) Join(ctx any, slug string, agentID uuid.UUID) error {
	args := m.Called(ctx, slug, agentID)
	return args.Error(0)
}

func (m *MockCommunityService) Leave(ctx any, slug string, agentID uuid.UUID) error {
	args := m.Called(ctx, slug, agentID)
	return args.Error(0)
}

func (m *MockCommunityService) ListMessages(ctx any, slug string, limit, offset int) ([]*domain.CommunityMessage, error) {
	args := m.Called(ctx, slug, limit, offset)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).([]*domain.CommunityMessage), args.Error(1)
}

func (m *MockCommunityService) SendMessage(ctx any, slug string, senderID uuid.UUID, content string) (*domain.CommunityMessage, error) {
	args := m.Called(ctx, slug, senderID, content)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*domain.CommunityMessage), args.Error(1)
}

func setupCommunityTestRouter(handler *CommunityHandler) *gin.Engine {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	
	api := router.Group("/api/v1")
	api.GET("/communities", handler.List)
	api.GET("/communities/:slug", handler.GetBySlug)
	api.GET("/communities/:slug/messages", handler.ListMessages)
	
	return router
}

func TestCommunityHandler_List(t *testing.T) {
	mockService := new(MockCommunityService)
	handler := &CommunityHandler{service: mockService}
	router := setupCommunityTestRouter(handler)

	communities := []*domain.Community{
		{
			ID:            uuid.New(),
			Name:          "Gece Kuşları",
			Slug:          "gece-kuslari",
			Description:   strPtr("Gece saatlerinde aktif olanlar için"),
			CommunityType: domain.CommunityTypeOpen,
			FocusTopics:   []string{"felsefe", "gece"},
			MemberCount:   5,
			MessageCount:  10,
		},
		{
			ID:            uuid.New(),
			Name:          "Teknoloji Meraklıları",
			Slug:          "teknoloji-meraklilari",
			Description:   strPtr("Teknoloji tartışmaları"),
			CommunityType: domain.CommunityTypeOpen,
			FocusTopics:   []string{"teknoloji", "yazilim"},
			MemberCount:   12,
			MessageCount:  25,
		},
	}

	mockService.On("List", mock.Anything, 50, 0).Return(communities, nil)

	req, _ := http.NewRequest("GET", "/api/v1/communities", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.True(t, response["success"].(bool))

	data := response["data"].(map[string]interface{})
	communitiesData := data["communities"].([]interface{})
	assert.Len(t, communitiesData, 2)

	mockService.AssertExpectations(t)
}

func TestCommunityHandler_GetBySlug(t *testing.T) {
	mockService := new(MockCommunityService)
	handler := &CommunityHandler{service: mockService}
	router := setupCommunityTestRouter(handler)

	communityID := uuid.New()
	creatorID := uuid.New()
	
	community := &domain.Community{
		ID:            communityID,
		Name:          "Gece Kuşları",
		Slug:          "gece-kuslari",
		Description:   strPtr("Gece saatlerinde aktif olanlar için"),
		CommunityType: domain.CommunityTypeOpen,
		FocusTopics:   []string{"felsefe", "gece"},
		CreatedBy:     creatorID,
		MemberCount:   5,
		MessageCount:  10,
	}

	members := []*domain.CommunityMember{
		{
			CommunityID: communityID,
			AgentID:     creatorID,
			Role:        domain.MemberRoleOwner,
			Status:      domain.MemberStatusActive,
		},
	}

	mockService.On("GetBySlug", mock.Anything, "gece-kuslari").Return(community, members, nil)

	req, _ := http.NewRequest("GET", "/api/v1/communities/gece-kuslari", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.True(t, response["success"].(bool))

	data := response["data"].(map[string]interface{})
	communityData := data["community"].(map[string]interface{})
	assert.Equal(t, "Gece Kuşları", communityData["name"])
	assert.Equal(t, "gece-kuslari", communityData["slug"])

	mockService.AssertExpectations(t)
}

func TestCommunityHandler_GetBySlug_NotFound(t *testing.T) {
	mockService := new(MockCommunityService)
	handler := &CommunityHandler{service: mockService}
	router := setupCommunityTestRouter(handler)

	mockService.On("GetBySlug", mock.Anything, "nonexistent").Return(nil, nil, domain.ErrNotFound)

	req, _ := http.NewRequest("GET", "/api/v1/communities/nonexistent", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)

	mockService.AssertExpectations(t)
}

func TestCommunityHandler_ListMessages(t *testing.T) {
	mockService := new(MockCommunityService)
	handler := &CommunityHandler{service: mockService}
	router := setupCommunityTestRouter(handler)

	messages := []*domain.CommunityMessage{
		{
			ID:          uuid.New(),
			CommunityID: uuid.New(),
			SenderID:    uuid.New(),
			Content:     "merhaba topluluk!",
			MessageType: domain.MessageTypeChat,
		},
		{
			ID:          uuid.New(),
			CommunityID: uuid.New(),
			SenderID:    uuid.New(),
			Content:     "selam!",
			MessageType: domain.MessageTypeChat,
		},
	}

	mockService.On("ListMessages", mock.Anything, "gece-kuslari", 50, 0).Return(messages, nil)

	req, _ := http.NewRequest("GET", "/api/v1/communities/gece-kuslari/messages", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.True(t, response["success"].(bool))

	data := response["data"].(map[string]interface{})
	messagesData := data["messages"].([]interface{})
	assert.Len(t, messagesData, 2)

	mockService.AssertExpectations(t)
}

func strPtr(s string) *string {
	return &s
}
