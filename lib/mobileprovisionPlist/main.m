//
//  main.m
//  mobileprovisionPlist
//
//  Created by David Keegan on 8/22/12.
//  Copyright (c) 2012 David Keegan. All rights reserved.
//

#import <Foundation/Foundation.h>

int main(int argc, const char * argv[]){
    @autoreleasepool{
        NSArray *arguments = [[NSProcessInfo processInfo] arguments];
        if([arguments count] > 1){
            NSString *plistString;
            NSString *fileString = [[NSString alloc] initWithContentsOfFile:arguments[1]];
            NSScanner *scanner = [[NSScanner alloc] initWithString:fileString];
            if([scanner scanUpToString:@"<?xml version=\"1.0\" encoding=\"UTF-8\"?>" intoString:nil]){
                NSString *scanString;
                if([scanner scanUpToString:@"</plist>" intoString:&scanString]){
                    plistString = [scanString stringByAppendingString:@"</plist>"];
                }
            }

            if([plistString length]){
                printf("%s\n", [plistString UTF8String]);
            }
        }
    }
    return 0;
}

