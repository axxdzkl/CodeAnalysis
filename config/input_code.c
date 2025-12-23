#include <stdio.h>

// 辅助计算函数
int calculate_tax(const int* base_price) {
    int rate = 5; // 假设税率
    int tax = (*base_price * rate) / 100;
    return tax;
}

// 主处理函数
void process_transaction(int* input_amount, int* final_price) {
    int raw_val = *input_amount;
    if (raw_val > 0) {
        int tax_val = calculate_tax(&raw_val);
        *final_price = raw_val + tax_val;
    } else {
        *final_price = 0;
    }
}

// 入口函数
int main() {
    int user_input = 1000;
    int output_total = 0;
    process_transaction(&user_input, &output_total);
    return 0;
}
