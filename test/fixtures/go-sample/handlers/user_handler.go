package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"github.com/example/go-sample-project/models"
	"github.com/example/go-sample-project/services"
)

// UserHandler handles user-related HTTP requests
type UserHandler struct {
	service *services.UserService
}

// NewUserHandler creates a new UserHandler
func NewUserHandler(service *services.UserService) *UserHandler {
	return &UserHandler{service: service}
}

// GetAllUsers returns all users
func (h *UserHandler) GetAllUsers(c *gin.Context) {
	users := h.service.GetAllUsers()
	c.JSON(http.StatusOK, users)
}

// GetUser returns a user by ID
func (h *UserHandler) GetUser(c *gin.Context) {
	id := c.Param("id")
	user, err := h.service.GetUserByID(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
		return
	}
	c.JSON(http.StatusOK, user)
}

// CreateUser creates a new user
func (h *UserHandler) CreateUser(c *gin.Context) {
	var input models.CreateUserInput
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	user := h.service.CreateUser(input)
	c.JSON(http.StatusCreated, user)
}
