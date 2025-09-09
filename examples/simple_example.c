/**
 * 简单示例程序
 * 
 * 这是一个简单的C程序，包含基本的控制结构，
 * 用于快速测试静态分析功能。
 */

#include <stdio.h>

// 全局变量
int counter = 0;

/**
 * 简单的加法函数
 */
int add(int a, int b) {
    counter++;
    return a + b;
}

/**
 * 条件判断函数
 */
int max(int a, int b) {
    counter++;
    if (a > b) {
        return a;
    } else {
        return b;
    }
}

/**
 * 循环计算阶乘
 */
int factorial(int n) {
    counter++;
    
    if (n <= 0) {
        return 1;
    }
    
    int result = 1;
    for (int i = 1; i <= n; i++) {
        result = result * i;
    }
    
    return result;
}

/**
 * 递归计算斐波那契数列
 */
int fibonacci(int n) {
    counter++;
    
    if (n <= 1) {
        return n;
    }
    
    return fibonacci(n - 1) + fibonacci(n - 2);
}

/**
 * 主函数
 */
int main() {
    printf("Simple Example Program\n");
    
    int x = 5;
    int y = 10;
    
    int sum = add(x, y);
    printf("Sum: %d\n", sum);
    
    int maximum = max(x, y);
    printf("Max: %d\n", maximum);
    
    int fact = factorial(5);
    printf("Factorial of 5: %d\n", fact);
    
    int fib = fibonacci(8);
    printf("Fibonacci of 8: %d\n", fib);
    
    printf("Total function calls: %d\n", counter);
    
    return 0;
}