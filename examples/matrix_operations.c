/**
 * 示例C程序 - 矩阵运算库
 * 
 * 这个程序实现了基本的矩阵运算功能，包括：
 * - 矩阵创建和初始化
 * - 矩阵加法和乘法
 * - 矩阵转置
 * - 矩阵打印
 * 
 * 用于测试复杂函数依赖关系和耦合度分析。
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_SIZE 100

// 全局配置变量
int debug_mode = 0;
int operation_counter = 0;
double error_tolerance = 0.0001;

// 矩阵结构定义
typedef struct {
    double data[MAX_SIZE][MAX_SIZE];
    int rows;
    int cols;
} Matrix;

/**
 * 创建新矩阵
 * @param rows 行数
 * @param cols 列数
 * @return 矩阵指针
 */
Matrix* create_matrix(int rows, int cols) {
    if (rows <= 0 || cols <= 0 || rows > MAX_SIZE || cols > MAX_SIZE) {
        if (debug_mode) {
            printf("Error: Invalid matrix dimensions %dx%d\n", rows, cols);
        }
        return NULL;
    }
    
    Matrix* matrix = (Matrix*)malloc(sizeof(Matrix));
    if (matrix == NULL) {
        if (debug_mode) {
            printf("Error: Memory allocation failed\n");
        }
        return NULL;
    }
    
    matrix->rows = rows;
    matrix->cols = cols;
    
    // 初始化为0
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            matrix->data[i][j] = 0.0;
        }
    }
    
    operation_counter++;
    return matrix;
}

/**
 * 销毁矩阵
 * @param matrix 要销毁的矩阵
 */
void destroy_matrix(Matrix* matrix) {
    if (matrix != NULL) {
        free(matrix);
        operation_counter++;
    }
}

/**
 * 设置矩阵元素
 * @param matrix 矩阵指针
 * @param row 行索引
 * @param col 列索引  
 * @param value 要设置的值
 * @return 1表示成功，0表示失败
 */
int set_element(Matrix* matrix, int row, int col, double value) {
    if (matrix == NULL) {
        return 0;
    }
    
    if (row < 0 || row >= matrix->rows || col < 0 || col >= matrix->cols) {
        if (debug_mode) {
            printf("Error: Index out of bounds (%d,%d)\n", row, col);
        }
        return 0;
    }
    
    matrix->data[row][col] = value;
    return 1;
}

/**
 * 获取矩阵元素
 * @param matrix 矩阵指针
 * @param row 行索引
 * @param col 列索引
 * @param value 输出值的指针
 * @return 1表示成功，0表示失败
 */
int get_element(Matrix* matrix, int row, int col, double* value) {
    if (matrix == NULL || value == NULL) {
        return 0;
    }
    
    if (row < 0 || row >= matrix->rows || col < 0 || col >= matrix->cols) {
        if (debug_mode) {
            printf("Error: Index out of bounds (%d,%d)\n", row, col);
        }
        return 0;
    }
    
    *value = matrix->data[row][col];
    return 1;
}

/**
 * 打印矩阵
 * @param matrix 要打印的矩阵
 * @param title 矩阵标题
 */
void print_matrix(Matrix* matrix, const char* title) {
    if (matrix == NULL) {
        printf("%s: NULL matrix\n", title ? title : "Matrix");
        return;
    }
    
    printf("%s (%dx%d):\n", title ? title : "Matrix", matrix->rows, matrix->cols);
    
    for (int i = 0; i < matrix->rows; i++) {
        printf("  ");
        for (int j = 0; j < matrix->cols; j++) {
            printf("%8.2f ", matrix->data[i][j]);
        }
        printf("\n");
    }
    printf("\n");
    
    operation_counter++;
}

/**
 * 矩阵加法
 * @param a 第一个矩阵
 * @param b 第二个矩阵
 * @return 结果矩阵，失败返回NULL
 */
Matrix* matrix_add(Matrix* a, Matrix* b) {
    if (a == NULL || b == NULL) {
        if (debug_mode) {
            printf("Error: NULL matrix in addition\n");
        }
        return NULL;
    }
    
    if (a->rows != b->rows || a->cols != b->cols) {
        if (debug_mode) {
            printf("Error: Matrix dimension mismatch in addition\n");
        }
        return NULL;
    }
    
    Matrix* result = create_matrix(a->rows, a->cols);
    if (result == NULL) {
        return NULL;
    }
    
    for (int i = 0; i < a->rows; i++) {
        for (int j = 0; j < a->cols; j++) {
            result->data[i][j] = a->data[i][j] + b->data[i][j];
        }
    }
    
    operation_counter++;
    return result;
}

/**
 * 矩阵减法
 * @param a 第一个矩阵
 * @param b 第二个矩阵
 * @return 结果矩阵，失败返回NULL
 */
Matrix* matrix_subtract(Matrix* a, Matrix* b) {
    if (a == NULL || b == NULL) {
        if (debug_mode) {
            printf("Error: NULL matrix in subtraction\n");
        }
        return NULL;
    }
    
    if (a->rows != b->rows || a->cols != b->cols) {
        if (debug_mode) {
            printf("Error: Matrix dimension mismatch in subtraction\n");
        }
        return NULL;
    }
    
    Matrix* result = create_matrix(a->rows, a->cols);
    if (result == NULL) {
        return NULL;
    }
    
    for (int i = 0; i < a->rows; i++) {
        for (int j = 0; j < a->cols; j++) {
            result->data[i][j] = a->data[i][j] - b->data[i][j];
        }
    }
    
    operation_counter++;
    return result;
}

/**
 * 矩阵乘法
 * @param a 第一个矩阵
 * @param b 第二个矩阵
 * @return 结果矩阵，失败返回NULL
 */
Matrix* matrix_multiply(Matrix* a, Matrix* b) {
    if (a == NULL || b == NULL) {
        if (debug_mode) {
            printf("Error: NULL matrix in multiplication\n");
        }
        return NULL;
    }
    
    if (a->cols != b->rows) {
        if (debug_mode) {
            printf("Error: Matrix dimension mismatch in multiplication\n");
            printf("  A: %dx%d, B: %dx%d\n", a->rows, a->cols, b->rows, b->cols);
        }
        return NULL;
    }
    
    Matrix* result = create_matrix(a->rows, b->cols);
    if (result == NULL) {
        return NULL;
    }
    
    for (int i = 0; i < a->rows; i++) {
        for (int j = 0; j < b->cols; j++) {
            double sum = 0.0;
            for (int k = 0; k < a->cols; k++) {
                sum += a->data[i][k] * b->data[k][j];
            }
            result->data[i][j] = sum;
        }
    }
    
    operation_counter++;
    return result;
}

/**
 * 矩阵转置
 * @param matrix 要转置的矩阵
 * @return 转置后的矩阵，失败返回NULL
 */
Matrix* matrix_transpose(Matrix* matrix) {
    if (matrix == NULL) {
        if (debug_mode) {
            printf("Error: NULL matrix in transpose\n");
        }
        return NULL;
    }
    
    Matrix* result = create_matrix(matrix->cols, matrix->rows);
    if (result == NULL) {
        return NULL;
    }
    
    for (int i = 0; i < matrix->rows; i++) {
        for (int j = 0; j < matrix->cols; j++) {
            result->data[j][i] = matrix->data[i][j];
        }
    }
    
    operation_counter++;
    return result;
}

/**
 * 创建单位矩阵
 * @param size 矩阵大小
 * @return 单位矩阵，失败返回NULL
 */
Matrix* create_identity_matrix(int size) {
    Matrix* matrix = create_matrix(size, size);
    if (matrix == NULL) {
        return NULL;
    }
    
    for (int i = 0; i < size; i++) {
        matrix->data[i][i] = 1.0;
    }
    
    operation_counter++;
    return matrix;
}

/**
 * 矩阵标量乘法
 * @param matrix 矩阵
 * @param scalar 标量值
 * @return 结果矩阵，失败返回NULL
 */
Matrix* matrix_scalar_multiply(Matrix* matrix, double scalar) {
    if (matrix == NULL) {
        if (debug_mode) {
            printf("Error: NULL matrix in scalar multiplication\n");
        }
        return NULL;
    }
    
    Matrix* result = create_matrix(matrix->rows, matrix->cols);
    if (result == NULL) {
        return NULL;
    }
    
    for (int i = 0; i < matrix->rows; i++) {
        for (int j = 0; j < matrix->cols; j++) {
            result->data[i][j] = matrix->data[i][j] * scalar;
        }
    }
    
    operation_counter++;
    return result;
}

/**
 * 检查矩阵是否相等
 * @param a 第一个矩阵
 * @param b 第二个矩阵
 * @return 1表示相等，0表示不相等
 */
int matrix_equals(Matrix* a, Matrix* b) {
    if (a == NULL || b == NULL) {
        return 0;
    }
    
    if (a->rows != b->rows || a->cols != b->cols) {
        return 0;
    }
    
    for (int i = 0; i < a->rows; i++) {
        for (int j = 0; j < a->cols; j++) {
            double diff = a->data[i][j] - b->data[i][j];
            if (diff < 0) diff = -diff;  // abs(diff)
            
            if (diff > error_tolerance) {
                return 0;
            }
        }
    }
    
    operation_counter++;
    return 1;
}

/**
 * 填充矩阵为随机值
 * @param matrix 要填充的矩阵
 * @param min_val 最小值
 * @param max_val 最大值
 */
void fill_random(Matrix* matrix, double min_val, double max_val) {
    if (matrix == NULL) {
        return;
    }
    
    for (int i = 0; i < matrix->rows; i++) {
        for (int j = 0; j < matrix->cols; j++) {
            // 简单的随机数生成（仅用于演示）
            double random_val = min_val + ((double)rand() / RAND_MAX) * (max_val - min_val);
            matrix->data[i][j] = random_val;
        }
    }
    
    operation_counter++;
}

/**
 * 演示函数 - 测试基本矩阵操作
 */
void demo_basic_operations() {
    printf("=== Basic Matrix Operations Demo ===\n");
    
    // 创建矩阵
    Matrix* a = create_matrix(3, 3);
    Matrix* b = create_matrix(3, 3);
    
    if (a == NULL || b == NULL) {
        printf("Failed to create matrices\n");
        return;
    }
    
    // 填充矩阵A
    set_element(a, 0, 0, 1.0); set_element(a, 0, 1, 2.0); set_element(a, 0, 2, 3.0);
    set_element(a, 1, 0, 4.0); set_element(a, 1, 1, 5.0); set_element(a, 1, 2, 6.0);
    set_element(a, 2, 0, 7.0); set_element(a, 2, 1, 8.0); set_element(a, 2, 2, 9.0);
    
    // 填充矩阵B
    set_element(b, 0, 0, 9.0); set_element(b, 0, 1, 8.0); set_element(b, 0, 2, 7.0);
    set_element(b, 1, 0, 6.0); set_element(b, 1, 1, 5.0); set_element(b, 1, 2, 4.0);
    set_element(b, 2, 0, 3.0); set_element(b, 2, 1, 2.0); set_element(b, 2, 2, 1.0);
    
    print_matrix(a, "Matrix A");
    print_matrix(b, "Matrix B");
    
    // 矩阵加法
    Matrix* sum = matrix_add(a, b);
    if (sum != NULL) {
        print_matrix(sum, "A + B");
        destroy_matrix(sum);
    }
    
    // 矩阵乘法
    Matrix* product = matrix_multiply(a, b);
    if (product != NULL) {
        print_matrix(product, "A * B");
        destroy_matrix(product);
    }
    
    // 矩阵转置
    Matrix* transpose_a = matrix_transpose(a);
    if (transpose_a != NULL) {
        print_matrix(transpose_a, "A^T");
        destroy_matrix(transpose_a);
    }
    
    // 清理
    destroy_matrix(a);
    destroy_matrix(b);
}

/**
 * 演示函数 - 测试复杂操作
 */
void demo_advanced_operations() {
    printf("=== Advanced Matrix Operations Demo ===\n");
    
    // 创建单位矩阵
    Matrix* identity = create_identity_matrix(4);
    if (identity != NULL) {
        print_matrix(identity, "4x4 Identity Matrix");
    }
    
    // 创建随机矩阵
    Matrix* random_matrix = create_matrix(3, 4);
    if (random_matrix != NULL) {
        fill_random(random_matrix, -10.0, 10.0);
        print_matrix(random_matrix, "Random Matrix (3x4)");
        
        // 标量乘法
        Matrix* scaled = matrix_scalar_multiply(random_matrix, 2.5);
        if (scaled != NULL) {
            print_matrix(scaled, "Scaled by 2.5");
            destroy_matrix(scaled);
        }
        
        destroy_matrix(random_matrix);
    }
    
    // 清理
    if (identity != NULL) {
        destroy_matrix(identity);
    }
}

/**
 * 主函数
 */
int main() {
    printf("=== Matrix Operations Library Demo ===\n");
    
    // 启用调试模式
    debug_mode = 1;
    
    // 初始化随机数生成器
    srand(42);  // 固定种子以获得可重现的结果
    
    // 运行演示
    demo_basic_operations();
    printf("\n");
    demo_advanced_operations();
    
    // 显示统计信息
    printf("=== Statistics ===\n");
    printf("Total operations performed: %d\n", operation_counter);
    printf("Error tolerance: %f\n", error_tolerance);
    printf("Debug mode: %s\n", debug_mode ? "ON" : "OFF");
    
    return 0;
}