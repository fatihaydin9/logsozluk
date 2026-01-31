package http

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/tenekesozluk/api-gateway/internal/domain"
)

// ErrorResponse represents a standardized API error response
type ErrorResponse struct {
	Success   bool          `json:"success"`
	Error     *ErrorDetail  `json:"error,omitempty"`
	RequestID string        `json:"request_id,omitempty"`
}

// ErrorDetail contains error details
type ErrorDetail struct {
	Code    string       `json:"code"`
	Message string       `json:"message"`
	Field   string       `json:"field,omitempty"`
	Details []FieldError `json:"details,omitempty"`
}

// FieldError represents a field-level validation error
type FieldError struct {
	Field   string `json:"field"`
	Code    string `json:"code"`
	Message string `json:"message"`
}

// MapError converts a domain error to an HTTP response
func MapError(c *gin.Context, err error) {
	requestID, _ := c.Get("request_id")
	reqIDStr, _ := requestID.(string)

	// Check if it's a domain error
	if domainErr, ok := err.(*domain.Error); ok {
		status := mapCategoryToStatus(domainErr.Category)

		response := ErrorResponse{
			Success:   false,
			RequestID: reqIDStr,
			Error: &ErrorDetail{
				Code:    domainErr.Code,
				Message: domainErr.Message,
				Field:   domainErr.Field,
			},
		}

		c.JSON(status, response)
		return
	}

	// Unknown error - return 500 without details
	c.JSON(http.StatusInternalServerError, ErrorResponse{
		Success:   false,
		RequestID: reqIDStr,
		Error: &ErrorDetail{
			Code:    "internal_error",
			Message: "An unexpected error occurred",
		},
	})
}

// mapCategoryToStatus maps domain error categories to HTTP status codes
func mapCategoryToStatus(category domain.ErrorCategory) int {
	switch category {
	case domain.ErrCategoryValidation:
		return http.StatusBadRequest // 400
	case domain.ErrCategoryUnauthorized:
		return http.StatusUnauthorized // 401
	case domain.ErrCategoryForbidden:
		return http.StatusForbidden // 403
	case domain.ErrCategoryNotFound:
		return http.StatusNotFound // 404
	case domain.ErrCategoryConflict:
		return http.StatusConflict // 409
	case domain.ErrCategoryInternal:
		return http.StatusInternalServerError // 500
	default:
		return http.StatusInternalServerError
	}
}

// RespondSuccess sends a successful JSON response
func RespondSuccess(c *gin.Context, data interface{}) {
	requestID, _ := c.Get("request_id")
	reqIDStr, _ := requestID.(string)

	c.JSON(http.StatusOK, gin.H{
		"success":    true,
		"data":       data,
		"request_id": reqIDStr,
	})
}

// RespondCreated sends a 201 Created response
func RespondCreated(c *gin.Context, data interface{}) {
	requestID, _ := c.Get("request_id")
	reqIDStr, _ := requestID.(string)

	c.JSON(http.StatusCreated, gin.H{
		"success":    true,
		"data":       data,
		"request_id": reqIDStr,
	})
}

// RespondNoContent sends a 204 No Content response
func RespondNoContent(c *gin.Context) {
	c.Status(http.StatusNoContent)
}

// RespondList sends a paginated list response
func RespondList(c *gin.Context, items interface{}, total int, limit, offset int) {
	requestID, _ := c.Get("request_id")
	reqIDStr, _ := requestID.(string)

	c.JSON(http.StatusOK, gin.H{
		"success":    true,
		"data":       items,
		"request_id": reqIDStr,
		"pagination": gin.H{
			"total":  total,
			"limit":  limit,
			"offset": offset,
		},
	})
}

// ValidationError creates a validation error response with multiple field errors
func ValidationError(c *gin.Context, fieldErrors []FieldError) {
	requestID, _ := c.Get("request_id")
	reqIDStr, _ := requestID.(string)

	c.JSON(http.StatusBadRequest, ErrorResponse{
		Success:   false,
		RequestID: reqIDStr,
		Error: &ErrorDetail{
			Code:    "validation_error",
			Message: "One or more fields are invalid",
			Details: fieldErrors,
		},
	})
}

// BadRequest sends a 400 Bad Request response
func BadRequest(c *gin.Context, code, message string) {
	requestID, _ := c.Get("request_id")
	reqIDStr, _ := requestID.(string)

	c.JSON(http.StatusBadRequest, ErrorResponse{
		Success:   false,
		RequestID: reqIDStr,
		Error: &ErrorDetail{
			Code:    code,
			Message: message,
		},
	})
}

// Unauthorized sends a 401 Unauthorized response
func Unauthorized(c *gin.Context, message string) {
	requestID, _ := c.Get("request_id")
	reqIDStr, _ := requestID.(string)

	c.JSON(http.StatusUnauthorized, ErrorResponse{
		Success:   false,
		RequestID: reqIDStr,
		Error: &ErrorDetail{
			Code:    "unauthorized",
			Message: message,
		},
	})
}

// Forbidden sends a 403 Forbidden response
func Forbidden(c *gin.Context, message string) {
	requestID, _ := c.Get("request_id")
	reqIDStr, _ := requestID.(string)

	c.JSON(http.StatusForbidden, ErrorResponse{
		Success:   false,
		RequestID: reqIDStr,
		Error: &ErrorDetail{
			Code:    "forbidden",
			Message: message,
		},
	})
}

// NotFound sends a 404 Not Found response
func NotFound(c *gin.Context, message string) {
	requestID, _ := c.Get("request_id")
	reqIDStr, _ := requestID.(string)

	c.JSON(http.StatusNotFound, ErrorResponse{
		Success:   false,
		RequestID: reqIDStr,
		Error: &ErrorDetail{
			Code:    "not_found",
			Message: message,
		},
	})
}
