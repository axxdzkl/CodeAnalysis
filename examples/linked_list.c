/**
 * 示例C程序 - 简单的链表实现
 * 
 * 这个程序实现了一个简单的单向链表，包含基本的操作：
 * - 创建节点
 * - 插入节点
 * - 搜索节点
 * - 删除节点
 * - 打印链表
 * 
 * 用于测试静态分析系统的各种功能。
 */

#include <stdio.h>
#include <stdlib.h>

// 全局变量
int list_size = 0;
int operation_count = 0;

// 链表节点结构
typedef struct Node {
    int data;
    struct Node* next;
} Node;

// 链表头指针
Node* head = NULL;

/**
 * 创建新节点
 * @param value 节点值
 * @return 新创建的节点指针
 */
Node* create_node(int value) {
    Node* new_node = (Node*)malloc(sizeof(Node));
    if (new_node == NULL) {
        printf("Memory allocation failed\n");
        return NULL;
    }
    
    new_node->data = value;
    new_node->next = NULL;
    operation_count++;
    
    return new_node;
}

/**
 * 在链表头部插入新节点
 * @param value 要插入的值
 * @return 1表示成功，0表示失败
 */
int insert_at_head(int value) {
    Node* new_node = create_node(value);
    if (new_node == NULL) {
        return 0;
    }
    
    new_node->next = head;
    head = new_node;
    list_size++;
    
    return 1;
}

/**
 * 在链表尾部插入新节点
 * @param value 要插入的值
 * @return 1表示成功，0表示失败
 */
int insert_at_tail(int value) {
    Node* new_node = create_node(value);
    if (new_node == NULL) {
        return 0;
    }
    
    if (head == NULL) {
        head = new_node;
    } else {
        Node* current = head;
        while (current->next != NULL) {
            current = current->next;
        }
        current->next = new_node;
    }
    
    list_size++;
    return 1;
}

/**
 * 搜索指定值在链表中的位置
 * @param value 要搜索的值
 * @return 找到返回位置索引，未找到返回-1
 */
int search(int value) {
    Node* current = head;
    int position = 0;
    
    while (current != NULL) {
        if (current->data == value) {
            operation_count++;
            return position;
        }
        current = current->next;
        position++;
    }
    
    operation_count++;
    return -1;
}

/**
 * 删除指定值的第一个节点
 * @param value 要删除的值
 * @return 1表示删除成功，0表示未找到
 */
int delete_value(int value) {
    if (head == NULL) {
        return 0;
    }
    
    // 如果要删除的是头节点
    if (head->data == value) {
        Node* temp = head;
        head = head->next;
        free(temp);
        list_size--;
        operation_count++;
        return 1;
    }
    
    // 搜索要删除的节点
    Node* current = head;
    while (current->next != NULL) {
        if (current->next->data == value) {
            Node* temp = current->next;
            current->next = temp->next;
            free(temp);
            list_size--;
            operation_count++;
            return 1;
        }
        current = current->next;
    }
    
    operation_count++;
    return 0;
}

/**
 * 打印链表中的所有元素
 */
void print_list() {
    Node* current = head;
    
    printf("List (%d elements): ", list_size);
    
    if (current == NULL) {
        printf("(empty)\n");
        return;
    }
    
    while (current != NULL) {
        printf("%d", current->data);
        current = current->next;
        if (current != NULL) {
            printf(" -> ");
        }
    }
    printf(" -> NULL\n");
}

/**
 * 获取链表长度
 * @return 链表中节点的数量
 */
int get_list_size() {
    return list_size;
}

/**
 * 清空整个链表
 */
void clear_list() {
    Node* current = head;
    Node* next;
    
    while (current != NULL) {
        next = current->next;
        free(current);
        current = next;
        operation_count++;
    }
    
    head = NULL;
    list_size = 0;
}

/**
 * 计算链表中所有元素的和
 * @return 所有元素的总和
 */
int sum_elements() {
    Node* current = head;
    int sum = 0;
    
    while (current != NULL) {
        sum += current->data;
        current = current->next;
    }
    
    operation_count++;
    return sum;
}

/**
 * 查找链表中的最大值
 * @return 最大值，如果链表为空返回-1
 */
int find_max() {
    if (head == NULL) {
        return -1;
    }
    
    Node* current = head;
    int max_value = current->data;
    
    while (current != NULL) {
        if (current->data > max_value) {
            max_value = current->data;
        }
        current = current->next;
    }
    
    operation_count++;
    return max_value;
}

/**
 * 反转链表
 */
void reverse_list() {
    Node* prev = NULL;
    Node* current = head;
    Node* next = NULL;
    
    while (current != NULL) {
        next = current->next;
        current->next = prev;
        prev = current;
        current = next;
    }
    
    head = prev;
    operation_count++;
}

/**
 * 主函数 - 演示链表操作
 */
int main() {
    printf("=== Linked List Demo ===\n");
    
    // 测试插入操作
    printf("\n1. Testing insertions:\n");
    insert_at_head(10);
    insert_at_head(20);
    insert_at_head(30);
    print_list();
    
    insert_at_tail(40);
    insert_at_tail(50);
    print_list();
    
    // 测试搜索操作
    printf("\n2. Testing search:\n");
    int pos = search(20);
    if (pos != -1) {
        printf("Found 20 at position %d\n", pos);
    } else {
        printf("20 not found\n");
    }
    
    pos = search(100);
    if (pos != -1) {
        printf("Found 100 at position %d\n", pos);
    } else {
        printf("100 not found\n");
    }
    
    // 测试统计操作
    printf("\n3. Testing statistics:\n");
    printf("List size: %d\n", get_list_size());
    printf("Sum of elements: %d\n", sum_elements());
    printf("Maximum value: %d\n", find_max());
    
    // 测试删除操作
    printf("\n4. Testing deletion:\n");
    printf("Before deletion: ");
    print_list();
    
    if (delete_value(20)) {
        printf("Successfully deleted 20\n");
    } else {
        printf("Failed to delete 20\n");
    }
    
    printf("After deletion: ");
    print_list();
    
    // 测试反转操作
    printf("\n5. Testing reverse:\n");
    printf("Before reverse: ");
    print_list();
    
    reverse_list();
    
    printf("After reverse: ");
    print_list();
    
    // 清理内存
    printf("\n6. Cleaning up:\n");
    clear_list();
    printf("List after cleanup: ");
    print_list();
    
    printf("\nTotal operations performed: %d\n", operation_count);
    printf("=== Demo completed ===\n");
    
    return 0;
}